from ..domain_type import process_domain_type
from stix2 import DomainName


def test_process_domain_type():
    domains = [
        {
            "0": DomainName(
                type="domain-name",
                spec_version="2.1",
                id="domain-name--4a602360-64e3-11eb-a7ae-07ed017e1990",
                value="localhost",
                resolves_to_refs=["ipv6-addr--4a602361-64e3-11eb-a7ae-07ed017e1990"],
                full_output="Mon Feb  1 23:14:25 2021.667496 |git@7f6319bfc741[17719] connect(3, {AF_INET, 127.0.0.53, 53}, 16) = 0",
                resolves_to_str="127.0.0.53",
                timestamp="Mon Feb  1 23:14:25 2021",
                allow_custom=True,
            )
        },
        {
            "0": DomainName(
                type="domain-name",
                spec_version="2.1",
                id="domain-name--4a602360-64e3-11eb-a7ae-07ed017e1990",
                value="fictional-domain-name",
                resolves_to_refs=["ipv6-addr--4a602361-64e3-11eb-a7ae-07ed017e1990"],
                full_output="Mon Feb  1 23:14:25 2021.667496 |git@7f6319bfc741[17719] connect(3, {AF_INET, 127.0.0.53, 53}, 16) = 0",
                resolves_to_str="this.is.an.ipaddress",
                timestamp="Mon Feb  1 23:14:25 2021",
                allow_custom=True,
            )
        },
    ]
    domain_patterns = process_domain_type(domains, 1)
    assert len(domain_patterns) == 2
