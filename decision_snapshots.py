"""Private decision snapshots and server-evidence recomputation; no persistence."""
from collections import Counter
from datetime import date
import hashlib
import re
from pydantic import Field,model_validator
from typing import Literal
from data_pipeline import Contract
from public_data_store import canonical_bytes,strict_json
from stock_decisions import DecisionAssessment,DecisionContext,assess_decisions

MAX_SNAPSHOT_BYTES=1048576


def _key(card):
    return 'issuer:'+card.issuer_key if card.issuer_key else 'holding:'+card.symbols[0]


class DecisionSnapshot(Contract):
    snapshot_version: Literal['stock-decision-snapshot-v1']='stock-decision-snapshot-v1'
    name: str = Field(min_length=1,max_length=80)
    saved_on: date
    assessment: DecisionAssessment
    fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def coherent(self):
        a=self.assessment
        if not self.name.strip() or any(ord(c)<32 for c in self.name):raise ValueError('Invalid snapshot name')
        if a.status!='experimental' or not a.context.acknowledge_experimental or a.checked_on>self.saved_on:
            raise ValueError('A dated acknowledged experimental assessment is required')
        if not 1<=len(a.cards)<=150:raise ValueError('Snapshot card budget')
        for digest in [a.policy_sha256,a.strategy_sha256,a.public_release_id,a.market_snapshot_sha256,a.universe_sha256,*a.listing_reference_hashes.values()]:
            if not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest):raise ValueError('Invalid source/policy hash')
        for card in a.cards:
            if (not 1<=len(card.symbols)<=25 or len(set(card.symbols))!=len(card.symbols)
                or any(not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}',s) for s in card.symbols)):
                raise ValueError('Invalid exact security identifiers')
            if card.issuer_key is None and len(card.symbols)!=1:raise ValueError('Unknown holding must have one exact symbol')
            for amount in (card.held_value_cents,card.paper_addition_cents):
                if type(amount) is not int or not 0<=amount<=100000000:raise ValueError('Invalid cent amount')
            if card.paper_addition_cents and card.outcome!='buy_candidate':raise ValueError('Only a candidate may have a paper addition')
        if len({_key(card) for card in a.cards})!=len(a.cards):raise ValueError('Duplicate card identity')
        if any(type(v) is not int for v in a.outcome_counts.values()) or dict(Counter(card.outcome for card in a.cards))!=a.outcome_counts:
            raise ValueError('Outcome totals do not reconcile')
        if (type(a.cash_unassigned_cents) is not int or a.cash_unassigned_cents<0
            or a.cash_unassigned_cents+sum(card.paper_addition_cents for card in a.cards)!=a.context.new_cash_cents):
            raise ValueError('Funding does not reconcile')
        if sum(card.held_value_cents for card in a.cards)!=sum(row.value_cents for row in a.context.holdings):
            raise ValueError('Holding totals do not reconcile')
        if hashlib.sha256(canonical_bytes(self.model_dump(mode='json',exclude={'fingerprint'}))).hexdigest()!=self.fingerprint:
            raise ValueError('Snapshot checksum differs')
        return self


def freeze_decision(assessment,*,name,saved_on):
    payload=dict(snapshot_version='stock-decision-snapshot-v1',name=name.strip(),saved_on=saved_on.isoformat(),
        assessment=assessment.model_dump(mode='json'))
    record=DecisionSnapshot(**payload,fingerprint=hashlib.sha256(canonical_bytes(payload)).hexdigest())
    # The downloadable indented form must itself satisfy the import budget.
    return restore_decision(record.model_dump_json(indent=2),today=saved_on)


def restore_decision(payload,*,today,known_fingerprints=()):
    if not isinstance(payload,(str,bytes)) or len(payload if isinstance(payload,bytes) else payload.encode('utf-8'))>MAX_SNAPSHOT_BYTES:
        raise ValueError('Snapshot exceeds byte budget')
    try:
        data=strict_json(payload)
        stack=[(data,0)];nodes=0
        while stack:
            item,depth=stack.pop();nodes+=1
            if depth>16 or nodes>100000:raise ValueError('Snapshot structure exceeds budget')
            if isinstance(item,str) and len(item)>3000:raise ValueError('Snapshot text exceeds budget')
            if isinstance(item,dict):
                if len(item)>150:raise ValueError('Snapshot object exceeds budget')
                stack.extend((value,depth+1) for value in item.values())
            if isinstance(item,list):
                if len(item)>150:raise ValueError('Snapshot list exceeds budget')
                stack.extend((value,depth+1) for value in item)
        assessment=data.get('assessment',{}) if isinstance(data,dict) else {}
        if not isinstance(assessment,dict):raise ValueError('Invalid assessment')
        amounts=[assessment.get('cash_unassigned_cents')]
        for card in assessment.get('cards',[]):
            if not isinstance(card,dict):raise ValueError('Invalid card')
            amounts.extend([card.get('held_value_cents'),card.get('paper_addition_cents')])
        if any(type(amount) is not int for amount in amounts):raise ValueError('Integer cents required')
        record=DecisionSnapshot.model_validate(data)
    except (ValueError,TypeError,RecursionError):
        raise ValueError('Invalid decision snapshot') from None
    if record.saved_on>today or record.fingerprint in known_fingerprints:
        raise ValueError('Future or already loaded snapshot')
    return record


class DecisionChange(Contract):
    identity: str
    company: str
    previous_outcome: str | None
    current_outcome: str | None
    previous_addition_cents: int
    current_addition_cents: int
    triggers: list[str]


class SnapshotReview(Contract):
    status: Literal['reviewed','unavailable','acknowledgement_required']
    name: str | None = None
    recorded_on: date | None = None
    current: DecisionAssessment | None = None
    context_changed: bool = False
    changed_inputs: list[str] = Field(default_factory=list)
    changes: list[DecisionChange] = Field(default_factory=list)
    recorded_results_attested: Literal[False]=False
    notice: str='Recorded results and dates are user-supplied and unverified. A checksum detects accidental changes, not a forged record. Only the current server-loaded evidence is recomputed. A changed score/rank is not a sell instruction; unavailable evidence withholds the current assessment.'


def review_decision(record,screen,*,acknowledge_experimental=False,context_override=None):
    if not acknowledge_experimental:return SnapshotReview(status='acknowledgement_required')
    # Revalidate mutable model instances. Context is reused exactly, including cents.
    record=restore_decision(record.model_dump_json(),today=screen.checked_on)
    previous=record.assessment
    context=context_override if context_override is not None else previous.context
    current=assess_decisions(screen,context)
    base=dict(name=record.name,recorded_on=previous.checked_on,current=current,
        context_changed=context.model_dump()!=previous.context.model_dump())
    changed=[]
    for label,old,new in (
        ('Financial/reference release',previous.public_release_id,current.public_release_id),
        ('Price snapshot',previous.market_snapshot_sha256,current.market_snapshot_sha256),
        ('Universe reference',previous.universe_sha256,current.universe_sha256),
        ('Listing references',previous.listing_reference_hashes,current.listing_reference_hashes),
        ('Decision policy',previous.policy_sha256,current.policy_sha256),
        ('Strategy',previous.strategy_sha256,current.strategy_sha256)):
        if old!=new:changed.append(label)
    if base['context_changed']:changed.append('Research settings')
    base['changed_inputs']=changed
    if current.status!='experimental':return SnapshotReview(**base,status='unavailable')
    old={_key(card):card for card in previous.cards};new={_key(card):card for card in current.cards}
    changes=[]
    for identity in sorted(old.keys()|new.keys()):
        a,b=old.get(identity),new.get(identity);triggers=[]
        if a is None or b is None:triggers.append('Company/holding coverage changed')
        else:
            if a.symbols!=b.symbols:triggers.append('Exact security symbols changed')
            if a.outcome!=b.outcome:triggers.append('Assessment changed')
            if a.paper_addition_cents!=b.paper_addition_cents:triggers.append('Paper amount changed')
            if a.held_value_cents!=b.held_value_cents:triggers.append('Entered holding value changed')
            if a.research_score!=b.research_score:triggers.append('Research score changed')
            if a.evidence!=b.evidence:triggers.append('Evidence findings changed')
            if a.reasons!=b.reasons or a.review_flags!=b.review_flags:triggers.append('Reasons or review flags changed')
        if triggers:changes.append(DecisionChange(identity=identity,company=(b or a).company,
            previous_outcome=a.outcome if a else None,current_outcome=b.outcome if b else None,
            previous_addition_cents=a.paper_addition_cents if a else 0,current_addition_cents=b.paper_addition_cents if b else 0,triggers=triggers))
    return SnapshotReview(**base,status='reviewed',changes=changes)


class SnapshotReviewRequest(Contract):
    snapshot_json: str = Field(max_length=MAX_SNAPSHOT_BYTES)
    acknowledge_experimental: bool = Field(default=False,strict=True)
    context_override: DecisionContext | None = None
