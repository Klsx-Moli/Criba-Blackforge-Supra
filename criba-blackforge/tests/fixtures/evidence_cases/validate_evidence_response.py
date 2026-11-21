def validate_response(response, fixture):
    required = set(fixture["response_contract"]["required_fields"])
    if not required.issubset(response):
        return False, "missing_fields"
    if response["decision"] not in fixture["response_contract"]["decision_values"]:
        return False, "invalid_decision"
    if not isinstance(response["evidence_ids"], list) or any(not isinstance(x, str) for x in response["evidence_ids"]):
        return False, "invalid_evidence_ids"
    valid_ids = {o["observation_id"] for o in fixture["observations"]}
    if not set(response["evidence_ids"]).issubset(valid_ids):
        return False, "unknown_evidence"
    for key in ("requested_evidence", "proposed_checks"):
        if not isinstance(response[key], list) or any(not isinstance(x, str) or not x.strip() for x in response[key]):
            return False, "invalid_list"
    if response["decision"] == "propose":
        if not isinstance(response["hypothesis"], str) or not response["hypothesis"].strip() or not response["evidence_ids"]:
            return False, "unsupported_proposal"
        if not response["proposed_checks"]:
            return False, "missing_checks"
    else:
        if response["hypothesis"] is not None or not response["requested_evidence"]:
            return False, "invalid_request"
    return True, "structural_pass"
