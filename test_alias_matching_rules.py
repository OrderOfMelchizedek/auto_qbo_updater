#!/usr/bin/env python3
"""
Test to demonstrate the alias matching rules without initial expansion.
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def demonstrate_alias_generation():
    """Show correct alias generation."""

    logger.info("=" * 60)
    logger.info("CORRECT ALIAS GENERATION")
    logger.info("=" * 60)

    examples = [
        {
            "extracted": "John A. Smith",
            "aliases": ["John Smith", "J. Smith", "Smith, John", "Smith, J.", "John A. Smith", "Smith, John A."],
            "explanation": "Comprehensive variations with/without middle initial",
        },
        {
            "extracted": "J. Lang",
            "aliases": ["J. Lang", "Lang, J."],
            "explanation": "Initial stays as initial - no expansion",
        },
        {
            "extracted": "Mary Johnson",
            "aliases": ["Mary Johnson", "M. Johnson", "Johnson, Mary", "Johnson, M."],
            "explanation": "Create initial version from first name",
        },
        {
            "extracted": "Robert James Wilson",
            "aliases": [
                "Robert James Wilson",
                "Robert Wilson",
                "R. Wilson",
                "Wilson, Robert",
                "Wilson, R.",
                "Wilson, Robert James",
                "R. J. Wilson",
                "Wilson, R. J.",
            ],
            "explanation": "Full variations for three-part names",
        },
        {
            "extracted": "Dr. Sarah Chen",
            "aliases": [
                "Dr. Sarah Chen",
                "Sarah Chen",
                "S. Chen",
                "Chen, Dr. Sarah",
                "Chen, Sarah",
                "Chen, S.",
                "Dr. S. Chen",
                "Chen, Dr. S.",
            ],
            "explanation": "Include versions with/without title",
        },
    ]

    for example in examples:
        logger.info(f"\nExtracted: '{example['extracted']}'")
        logger.info(f"Aliases: {example['aliases']}")
        logger.info(f"Rule: {example['explanation']}")

    logger.info("\n" + "=" * 60)
    logger.info("WHAT NOT TO DO")
    logger.info("=" * 60)

    wrong_examples = [
        {
            "extracted": "J. Lang",
            "wrong": ["John Lang", "James Lang", "J Lang"],
            "why": "Don't expand J. to John/James, don't remove periods",
        },
        {
            "extracted": "Dr. Smith",
            "wrong": ["Doctor Smith", "David Smith"],
            "why": "Don't expand Dr. or guess first names",
        },
        {"extracted": "B. Gates", "wrong": ["Bill Gates", "William Gates"], "why": "B. is B., not Bill or William"},
    ]

    for example in wrong_examples:
        logger.info(f"\nExtracted: '{example['extracted']}'")
        logger.info(f"❌ WRONG: {example['wrong']}")
        logger.info(f"Why: {example['why']}")


def demonstrate_matching_logic():
    """Show how matching works."""

    logger.info("\n" + "=" * 60)
    logger.info("MATCHING LOGIC EXAMPLES")
    logger.info("=" * 60)

    test_cases = [
        {
            "alias": "J. Lang",
            "qbo_name": "Lang, John D. & Esther A.",
            "match": True,
            "reason": "Last name 'Lang' matches AND structure matches (both have comma)",
        },
        {
            "alias": "Lang, J.",
            "qbo_name": "Lang, John D. & Esther A.",
            "match": True,
            "reason": "Format matches: 'Lang, J.' fits pattern of 'Lang, John...'",
        },
        {
            "alias": "J. Smith",
            "qbo_name": "Johnson, Smith & Associates",
            "match": False,
            "reason": "Last names don't match (Smith vs Johnson)",
        },
        {
            "alias": "Smith",
            "qbo_name": "Smith, John and Jane",
            "match": True,
            "reason": "'Smith' is contained in the QBO name",
        },
        {
            "alias": "J. Collins",
            "qbo_name": "Collins, Jonelle",
            "match": True,
            "reason": "Last name matches AND 'J.' could be Jonelle",
        },
        {
            "alias": "J. Collins",
            "qbo_name": "Collins, Robert",
            "match": False,
            "reason": "J. doesn't match Robert (no 'J' in Robert)",
        },
    ]

    for test in test_cases:
        logger.info(f"\nAlias: '{test['alias']}'")
        logger.info(f"QBO: '{test['qbo_name']}'")
        logger.info(f"Match: {'✅' if test['match'] else '❌'}")
        logger.info(f"Reason: {test['reason']}")


if __name__ == "__main__":
    demonstrate_alias_generation()
    demonstrate_matching_logic()
