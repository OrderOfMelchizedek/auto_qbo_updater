#!/usr/bin/env python3
"""
Demonstrate how comprehensive aliases improve matching success.
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def demonstrate_matching_scenarios():
    """Show how comprehensive aliases help matching."""

    logger.info("=" * 70)
    logger.info("HOW COMPREHENSIVE ALIASES IMPROVE MATCHING")
    logger.info("=" * 70)

    scenarios = [
        {
            "check_name": "John A. Smith",
            "aliases": ["John Smith", "J. Smith", "Smith, John", "Smith, J.", "John A. Smith", "Smith, John A."],
            "qbo_customers": [
                ("Smith, John", True, "Matches 'Smith, John' alias"),
                ("John Smith", True, "Matches 'John Smith' alias"),
                ("Smith, J.", True, "Matches 'Smith, J.' alias"),
                ("Smith, John Anthony", True, "Matches via 'Smith, John' alias"),
                ("J. A. Smith", False, "No exact match in aliases"),
            ],
        },
        {
            "check_name": "Robert Wilson",
            "aliases": ["Robert Wilson", "R. Wilson", "Wilson, Robert", "Wilson, R."],
            "qbo_customers": [
                ("Wilson, R.", True, "Matches 'Wilson, R.' alias"),
                ("R. Wilson", True, "Matches 'R. Wilson' alias"),
                ("Wilson, Robert J.", True, "Matches via 'Wilson, Robert' alias"),
                ("Bob Wilson", False, "Bob is not in aliases"),
            ],
        },
        {
            "check_name": "Mary Jane Johnson",
            "aliases": [
                "Mary Jane Johnson",
                "Mary Johnson",
                "M. Johnson",
                "Johnson, Mary Jane",
                "Johnson, Mary",
                "Johnson, M.",
                "M. J. Johnson",
                "Johnson, M. J.",
            ],
            "qbo_customers": [
                ("Johnson, Mary", True, "Matches 'Johnson, Mary' alias"),
                ("M. J. Johnson", True, "Matches 'M. J. Johnson' alias"),
                ("Mary Johnson", True, "Matches 'Mary Johnson' alias (without middle)"),
                ("Johnson, M.", True, "Matches 'Johnson, M.' alias"),
            ],
        },
    ]

    for scenario in scenarios:
        logger.info(f"\nExtracted from check: '{scenario['check_name']}'")
        logger.info(f"Generated aliases: {len(scenario['aliases'])} variations")
        logger.info("\nMatching results:")

        for qbo_name, matches, reason in scenario["qbo_customers"]:
            status = "✅" if matches else "❌"
            logger.info(f"  {status} QBO: '{qbo_name}' - {reason}")

    logger.info("\n" + "=" * 70)
    logger.info("KEY BENEFITS OF COMPREHENSIVE ALIASES")
    logger.info("=" * 70)

    benefits = [
        "1. Handles different formatting preferences (John Smith vs Smith, John)",
        "2. Matches when QBO has initials but check has full name",
        "3. Matches when check has middle initial but QBO doesn't",
        "4. Increases match rate without making assumptions",
        "5. Works with various data entry conventions",
    ]

    for benefit in benefits:
        logger.info(f"\n{benefit}")


if __name__ == "__main__":
    demonstrate_matching_scenarios()
