import logging

from .helper_functions import match_patterns_on_reports

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

    def match_ratio(self, accumulated_reports=None):
        if accumulated_reports:
            self.update_matched_reports(accumulated_reports)
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

    def update_matched_reports(self, accumulated_reports):
        match_patterns_on_reports(accumulated_reports, [self])


def process_domain_type(domains, accumulated_reports):
    domain_patterns = {}
    for domain in domains:
        domain_name = domain["0"]["value"]

        if domain_name in domain_patterns:
            domain_pattern = domain_patterns[domain_name]
        else:
            domain_pattern = DomainPattern(len(accumulated_reports))
            domain_pattern.domain = domain_name

        if "resolves_to_refs" in domain["0"]:
            ip = domain["0"]["resolves_to_str"]
            if ip not in domain_pattern.ips:
                domain_pattern.ips.append(ip)

        domain_patterns[domain_name] = domain_pattern

    domain_patterns = list(domain_patterns.values())
    match_patterns_on_reports(accumulated_reports, domain_patterns)
    return domain_patterns
