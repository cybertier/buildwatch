import logging
from typing import List

from .helper_functions import DomainData

log = logging.getLogger(__name__)


class DomainPattern:
    def __hash__(self):
        return hash(repr(self))

    def __init__(self, domain):
        self.domain = domain
        self.ips = []
        self.matched_reports = []

    def __eq__(self, other):
        if not isinstance(other, DomainPattern):
            return False
        return self.observation_expression() == other.observation_expression()

    def observation_expression(self):
        return (
            "["
            + " OR ".join(
                [f"domain-name:value = '{self.domain}'"]
                + ["domain-name:resolves_to_str = " "'{}'".format(x) for x in self.ips]
            )
            + "]"
        )


def process_domain_type(domains: List[DomainData]) -> List[str]:
    domain_patterns = {}
    for domain in domains:
        if domain.name in domain_patterns:
            domain_pattern = domain_patterns[domain.name]
        else:
            domain_pattern = DomainPattern(domain.name)

        if domain.ip not in domain_pattern.ips:
            domain_pattern.ips.append(domain.ip)

        domain_patterns[domain.name] = domain_pattern
    return [pattern.observation_expression() for pattern in domain_patterns.values()]
