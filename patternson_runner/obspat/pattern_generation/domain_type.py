import logging
from typing import List

log = logging.getLogger(__name__)

from .helper_functions import DomainData


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
        domain_name = domain.name

        if domain_name in domain_patterns:
            domain_pattern = domain_patterns[domain_name]
        else:
            domain_pattern = DomainPattern(domain_name)

        if domain.ip not in domain_pattern.ips:
            domain_pattern.ips.append(domain.ip)

        domain_patterns[domain_name] = domain_pattern

    observation_expressions = []
    for key, value in domain_patterns.items():
        observation_expressions.append(value.observation_expression())
    return observation_expressions
