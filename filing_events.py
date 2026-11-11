"""Conservative SEC submissions metadata normalization, without article inference."""

from datetime import date
import re

from market_sources import source_for_id


FORMS={"8-K","8-K/A","10-K","10-K/A","10-Q","10-Q/A"}
ITEMS={"1.01":"Material agreement disclosed", "1.02":"Material agreement termination disclosed",
       "2.01":"Acquisition or disposal disclosed", "2.02":"Results of operations disclosed",
       "2.05":"Exit or disposal costs disclosed", "5.02":"Leadership or compensation disclosure",
       "7.01":"Regulation FD disclosure", "8.01":"Other events disclosed"}


def normalize_submissions(source_id, payload, *, as_of):
    source=source_for_id(source_id)
    if source.format!="submissions_json":raise ValueError("Not a submissions source")
    expected=int(source_id.removeprefix("sec_submissions_cik"))
    # SEC submissions encodes CIK as a zero-padded string, unlike companyfacts.
    cik=payload.get("cik")
    if isinstance(cik,bool) or not isinstance(cik,(str,int)) or not re.fullmatch(r"[0-9]{1,10}",str(cik)) or int(cik)!=expected:
        raise ValueError("Submissions issuer does not match registered CIK")
    recent=payload["filings"]["recent"]
    name=payload.get("name")
    if not isinstance(name,str) or not 1<=len(name.strip())<=300:raise ValueError("Missing issuer name")
    required=("accessionNumber","filingDate","form","primaryDocument")
    if any(not isinstance(recent.get(key),list) for key in required):raise ValueError("Missing submissions columns")
    count=len(recent["accessionNumber"])
    # Busy issuers may have far more than 1,000 filings in the mandated recent
    # year. Keep an explicit ceiling in addition to the transport byte limit.
    if count>50000 or any(len(value)!=count for value in recent.values() if isinstance(value,list)):
        raise ValueError("Unaligned or oversized submissions columns")
    if "items" in recent and not isinstance(recent["items"],list):raise ValueError("Invalid item column")
    rows=[]; seen=set(); future=0
    for index in range(count):
        form=recent["form"][index]
        if form not in FORMS:continue
        filed=date.fromisoformat(recent["filingDate"][index])
        if filed>as_of:future+=1;continue
        accession,document=recent["accessionNumber"][index],recent["primaryDocument"][index]
        if not isinstance(accession,str) or not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}",accession):
            raise ValueError("Invalid accession")
        if not isinstance(document,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}\.html?",document) or ".." in document:
            raise ValueError("Unsafe primary document")
        if accession in seen:raise ValueError("Duplicate filing accession")
        seen.add(accession)
        items=recent.get("items",[""]*count)[index]
        if not isinstance(items,str):raise ValueError("Invalid item metadata")
        codes=[code.strip() for code in items.split(",") if code.strip()]
        if any(not re.fullmatch(r"[0-9]{1,2}\.[0-9]{2}",code) for code in codes):
            raise ValueError("Invalid item code")
        topics=[ITEMS[code] for code in codes if code in ITEMS]
        rows.append(dict(record_id=accession,cik=expected,form=form,filed_on=filed.isoformat(),
            items=codes,topics=topics,headline="; ".join(topics) if topics else
            "Annual financial report" if form.startswith("10-K") else "Quarterly financial report" if form.startswith("10-Q") else "Current report",
            source_url=f"https://www.sec.gov/Archives/edgar/data/{expected}/{accession.replace('-','')}/{document}"))
    rows.sort(key=lambda row:(row["filed_on"],row["record_id"]),reverse=True)
    # One envelope record permits a verified empty feed; no filing is invented.
    return dict(adapter_version="public-normalization-v1",kind="issuer_filing_events",
        observation_date=max((row["filed_on"] for row in rows),default=None),
        records=[dict(record_id=f"sec:{expected:010d}",cik=expected,issuer_name=name,filings=rows)],
        summary=dict(filing_count=len(rows),future_filings_excluded=future,complete_news_coverage=False,
                     observation_date_basis="filing_date_not_event_occurrence"))
