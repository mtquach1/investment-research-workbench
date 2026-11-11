"""Reported point-in-time share evidence; never diluted weighted-average shares."""

from datetime import date
from decimal import Decimal, InvalidOperation


def reported_share_reference(company,*,as_of):
    observations=company.get("facts",{}).get("dei",{}).get("EntityCommonStockSharesOutstanding",{}).get("units",{}).get("shares",[])
    valid=[]
    for row in observations:
        try:
            end,filed=date.fromisoformat(row["end"]),date.fromisoformat(row["filed"])
            value=Decimal(str(row["val"]))
            if (isinstance(row["val"],bool) or not value.is_finite() or not 0<value<=Decimal("1e15") or value!=value.to_integral_value()
                    or row.get('start') is not None
                    or not end<=filed<=as_of or row.get("form") not in ("10-K","10-K/A","10-Q","10-Q/A") or not row.get("accn")):
                continue
            valid.append(dict(measured_on=end.isoformat(),filed_on=filed.isoformat(),shares=str(value),
                accession=row["accn"],tag="dei:EntityCommonStockSharesOutstanding",unit="shares"))
        except (KeyError,TypeError,ValueError,InvalidOperation):continue
    if not valid:return {"status":"unavailable","evidence":None}
    latest=max((row["measured_on"],row["filed_on"]) for row in valid)
    candidates=[row for row in valid if (row["measured_on"],row["filed_on"])==latest]
    if len({row["shares"] for row in candidates})!=1:return {"status":"ambiguous","evidence":None}
    return {"status":"reported_point","evidence":sorted(candidates,key=lambda row:row["accession"])[-1]}
