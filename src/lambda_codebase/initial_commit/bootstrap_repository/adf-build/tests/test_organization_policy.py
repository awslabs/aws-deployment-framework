from organization_policy import OrganizationPolicy

def test_return_policy_name_with_scp_and_filename():
    policy_type = "SERVICE_CONTROL_POLICY"
    path="test-path"
    filename="scp-test.json"
    policy_name = OrganizationPolicy.return_policy_name(policy_type=policy_type, target_path=path, policy_filename=filename)
    assert policy_name == f"adf-scp-{path}--{filename}"

def test_return_policy_name_with_scp_and_no_filename():
    policy_type = "SERVICE_CONTROL_POLICY"
    path="test-path"
    policy_name = OrganizationPolicy.return_policy_name(policy_type=policy_type, target_path=path, policy_filename="scp.json")
    assert policy_name == f"adf-scp-{path}"    

def test_return_policy_name_with_tagging_policy_and_filename():
    policy_type = "TAGGING_POLICY"
    path="test-path"
    filename="tagging-policy-test.json"
    policy_name = OrganizationPolicy.return_policy_name(policy_type=policy_type, target_path=path, policy_filename=filename)
    assert policy_name == f"adf-tagging-policy-{path}--{filename}"

def test_return_policy_name_with_tagging_policy_and_no_filename():
    policy_type = "TAGGING_POLICY"
    path="test-path"
    policy_name = OrganizationPolicy.return_policy_name(policy_type=policy_type, target_path=path, policy_filename="tagging-policy.json")
    assert policy_name == f"adf-tagging-policy-{path}"       
