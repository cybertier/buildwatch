import logging
from typing import List, Dict
from stix2 import DomainName

log = logging.getLogger(__name__)


class DomainPattern:
    def __hash__(self):
        return hash(repr(self))

    def __init__(self, amount_of_reports):
        self.domain = None
        self.ips = []
        self.matched_reports = []
        self.amount_of_reports = amount_of_reports

    def __eq__(self, other):
        if not isinstance(other, DomainPattern):
            return False
        return self.observation_expression() == other.observation_expression()

    def match_ratio(self):
        return len(self.matched_reports) / self.amount_of_reports

    def observation_expression(self):
        return (
            "["
            + " OR ".join(
                [f"domain-name:value = '{self.domain}'"]
                + ["domain-name:resolves_to_str = " "'{}'".format(x) for x in self.ips]
            )
            + "]"
        )


def process_domain_type(domains: List[Dict[str, DomainName]], number_of_reports: int) -> List:
    domain_patterns = {}
    for domain in domains:
        domain_name = domain["0"]["value"]

        if domain_name in domain_patterns:
            domain_pattern = domain_patterns[domain_name]
        else:
            domain_pattern = DomainPattern(number_of_reports)
            domain_pattern.domain = domain_name

        if "resolves_to_refs" in domain["0"]:
            ip = domain["0"]["resolves_to_str"]
            if ip not in domain_pattern.ips:
                domain_pattern.ips.append(ip)

        domain_patterns[domain_name] = domain_pattern

    domain_patterns = list(domain_patterns.values())
    return domain_patterns
