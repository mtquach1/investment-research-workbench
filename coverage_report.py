"""Reproducible local audit matrices, separate from private scenario exports."""

from data_pipeline import load_release, read_table
from issuer_mapping import exact_issuer_matches


def coverage_report(root):
    digest,manifest=load_release(root)
    def table(name):
        return read_table(root,manifest.tables[name]) if name in manifest.tables else None
    geography=table("census_zcta_county_2020")
    values=table("zillow_sfr_value_zip")
    rents=table("zillow_mixed_rent_zip")
    price_dates=values["summary"]["latest_by_entity"] if values else {}
    rent_dates=rents["summary"]["latest_by_entity"] if rents else {}
    rental_rows=[]
    for row in geography["records"] if geography else []:
        entity=row["zcta"]
        rental_rows.append({"zcta":entity,"geography_vintage":2020,"county_land_share":row["county_land_share"],
            "shared_county":row["shared_county"],"largest_land_county":row["largest_land_county"],
            "current_usps_membership_verified":False,
            "sfr_value_last_observation":price_dates.get(entity),
            "mixed_rent_last_observation":rent_dates.get(entity),
            "mixed_rent_compatible_with_sfr_underwriting":False,
            "sfr_zip_rent_status":"unavailable","property_cashflow_screening_supported":False})
    proxy=table("ivv_holdings_proxy")
    mapping=table("sec_ticker_exchange")
    matches={item["security_id"]:item for item in exact_issuer_matches(
        proxy["records"] if proxy else [],mapping["records"] if mapping else [])}
    stock_rows=[]
    for row in proxy["records"] if proxy else []:
        match=matches[row["security_id"]]
        stock_rows.append({"security_id":row["security_id"],"provider_ticker":row["ticker"],"sector":row["sector"],
            "holdings_observation_date":proxy["observation_date"],"membership_status":"ETF_proxy_only",
            "issuer_mapping_status":match["status"],"issuer_id":match["issuer_id"],"annual_financials_status":"not_joined",
            "snapshot_price_present":row["has_snapshot_price"],"validated_valuation_status":"unavailable",
            "price_history_status":"not_joined","benchmark_status":"unavailable","recommendation_ready":False})
    candidates={row["zcta"] for row in rental_rows}
    financial_samples=[]
    for key,reference in manifest.tables.items():
        if reference.kind!="annual_financial_sample":
            continue
        issuer=read_table(root,reference)["records"][0]
        financial_samples.append({"source_id":key,**reference.summary,"source_sha256":reference.source_sha256,
            **{name:issuer[name] for name in ("issuer_id","cik","issuer","period_start","period_end","accession","metric_status","issues","basis")}})
    return {"schema_version":"public-coverage-matrices-v1","release_id":digest,"as_of":manifest.as_of.isoformat(),
        "scope":"local_public_source_audit_not_private_plan_or_live_recommendations",
        "rental_candidates":rental_rows,"stock_proxy_securities":stock_rows,
        "provider_county_labels_outside_census_candidate_set":sorted((set(price_dates)|set(rent_dates))-candidates),
        "financial_samples":financial_samples,
        "sources":[{"source_id":key,"source_sha256":reference.source_sha256,
            "artifact_sha256":reference.artifact_sha256,"retrieved_at":reference.retrieved_at.isoformat(),
            "observation_date":reference.observation_date.isoformat() if reference.observation_date else None,
            "kind":reference.kind,"row_count":reference.row_count,"policy":reference.policy,"state":reference.state}
            for key,reference in sorted(manifest.tables.items())],
        "failures":{key:value.model_dump(mode="json") for key,value in manifest.failures.items()},
        "limitations":["No raw price/rent ratio is interpreted as a property return.",
            "Issuer samples and the IBM demo are not silently joined to holdings tickers without verified security mappings.",
            "Full stock-universe metrics and current USPS membership remain unverified.",
            "Local audit export does not grant permission to redistribute provider records."]}
