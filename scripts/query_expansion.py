# ============================================================
# TT&T DOMAIN QUERY EXPANSION
# ============================================================
#
# Converts natural customer language into:
#
#   1. intent
#   2. expanded semantic query for BGE
#   3. expanded lexical query for PostgreSQL FTS
#   4. preferred knowledge-base categories
#
# IMPORTANT:
#
# preferred_categories MUST match the category values stored
# in PostgreSQL exactly.
#
# Supported TT&T categories:
#
#   account
#   activation_fee
#   billing_promotion
#   billing_tax
#   cancellation
#   device
#   faq
#   international
#   new_connection
#   lost_device
#   network
#   payment
#   plans
#   plan_data
#   number_porting
#   security
#   sim_esim
#   support
#   troubleshooting_calls
#   troubleshooting_data
#
# ============================================================


# ============================================================
# HELPERS
# ============================================================

def contains_any(
    text: str,
    terms: list[str],
) -> bool:
    """
    Return True if at least one term occurs in text.
    """

    return any(
        term in text
        for term in terms
    )


def contains_all_groups(
    text: str,
    groups: list[list[str]],
) -> bool:
    """
    At least one term from EVERY group must occur.

    Example:

        groups = [
            ["phone", "device"],
            ["lost", "missing"],
        ]

    "my phone is missing" -> True
    """

    return all(
        contains_any(text, group)
        for group in groups
    )


def build_analysis(
    query: str,
    intent: str,
    semantic_terms: str,
    keyword_query: str,
    preferred_categories: list[str],
) -> dict:
    """
    Construct the structure expected by hybrid_retrieval.py.
    """

    return {
        "intent": intent,

        # Keep untouched user wording for reranking.
        "original_query": query,

        # BGE receives richer domain terminology.
        "semantic_query": (
            f"{query}\n"
            f"Relevant telecom concepts: {semantic_terms}"
        ),

        # PostgreSQL websearch_to_tsquery receives this.
        "keyword_query": keyword_query,

        # Exact DB metadata category names.
        "preferred_categories": preferred_categories,
    }


# ============================================================
# MAIN ANALYZER
# ============================================================

def analyze_query(query: str) -> dict:
    """
    Deterministic TT&T telecom query analyzer.

    Specific intents are deliberately checked before broad
    intents so generic rules do not override better matches.
    """

    normalized = (
        query.lower()
        .replace("tt&t", "ttt")
        .replace("e-sim", "esim")
        .replace("wi-fi", "wifi")
        .strip()
    )


    # ========================================================
    # 1. LOST / STOLEN DEVICE
    # Category: lost_device
    # Document: LOST-01
    # ========================================================

    device_words = [
        "phone",
        "device",
        "mobile",
        "handset",
        "iphone",
        "android",
    ]

    loss_words = [
        "lost",
        "missing",
        "misplaced",
        "stolen",
        "dropped",
        "gone",
        "can't find",
        "cannot find",
        "cant find",
        "can't get it back",
        "cannot get it back",
        "cant get it back",
        "don't know where",
        "do not know where",
        "left my phone",
        "left my device",
        "someone stole",
        "was stolen",
        "left it somewhere",
    ]

    if contains_all_groups(
        normalized,
        [
            device_words,
            loss_words,
        ],
    ):
        return build_analysis(
            query=query,
            intent="lost_device",

            semantic_terms=(
                "lost phone, stolen phone, missing mobile device, "
                "misplaced handset, report a lost device, "
                "secure a stolen phone, suspend the affected "
                "mobile line"
            ),

            keyword_query=(
                '"lost phone" OR '
                '"stolen phone" OR '
                '"missing phone" OR '
                '"lost device" OR '
                '"stolen device" OR '
                '"suspend line"'
            ),

            preferred_categories=[
                "lost_device",
            ],
        )


    # ========================================================
    # 2. NUMBER PORTING
    # Category: number_porting
    # Document: PORT-01
    # ========================================================

    number_words = [
        "number",
        "phone number",
        "mobile number",
        "cell number",
    ]

    porting_words = [
        "transfer",
        "port",
        "porting",
        "bring",
        "move",
        "keep",
        "same",
        "existing",
        "old number",
        "switch carrier",
        "switch carriers",
    ]

    if contains_all_groups(
        normalized,
        [
            number_words,
            porting_words,
        ],
    ):
        return build_analysis(
            query=query,
            intent="number_porting",

            semantic_terms=(
                "number porting, port-in, transfer an existing "
                "phone number to TT&T, keep the same mobile "
                "number when changing carriers, bring a number "
                "from another carrier"
            ),

            keyword_query=(
                '"number transfer" OR '
                '"number porting" OR '
                '"existing number" OR '
                '"keep my number" OR '
                '"keep existing number" OR '
                '"same number" OR '
                '"transfer procedure" OR '
                'porting'
            ),

            preferred_categories=[
                "number_porting",
            ],
        )


    # ========================================================
    # 3. CANCELLATION
    # Category: cancellation
    # Document: CANCEL-01
    # ========================================================

    cancellation_words = [
        "cancel",
        "cancellation",
        "terminate",
        "disconnect",
        "close my account",
        "close account",
        "end my service",
        "stop my service",
        "stop service",
        "leave ttt",
        "leaving ttt",
        "switch away",
        "switching away",
        "switching from ttt",
        "no longer want service",
        "don't want service anymore",
        "do not want service anymore",
        "shut off my service",
        "close my service",
    ]

    if contains_any(
        normalized,
        cancellation_words,
    ):
        return build_analysis(
            query=query,
            intent="cancellation",

            semantic_terms=(
                "TT&T service cancellation, terminate mobile "
                "service, close an account, disconnect a line, "
                "leave TT&T, stop mobile service, final bill "
                "after cancellation"
            ),

            keyword_query=(
                'cancel OR '
                'cancellation OR '
                '"cancel service" OR '
                '"close account" OR '
                '"terminate service" OR '
                '"disconnect service" OR '
                '"final bill"'
            ),

            preferred_categories=[
                "cancellation",
            ],
        )


    # ========================================================
    # 4. ACTIVATION FEE
    #
    # IMPORTANT:
    # This MUST remain before new_connection.
    #
    # Category: activation_fee
    # Document: BILL-ACT-01
    # ========================================================

    activation_context = [
        "activate",
        "activated",
        "activating",
        "activation",
        "new line",
        "added a line",
        "add a line",
        "opened a line",
        "started a line",
    ]

    charge_context = [
        "fee",
        "charge",
        "charged",
        "cost",
        "one-time",
        "one time",
        "bill",
        "billing",
        "$35",
        "35 dollar",
    ]

    if contains_all_groups(
        normalized,
        [
            activation_context,
            charge_context,
        ],
    ):
        return build_analysis(
            query=query,
            intent="activation_fee",

            semantic_terms=(
                "TT&T activation fee, one-time activation charge, "
                "charge for activating a new mobile line, "
                "$35 activation fee appearing on the activation "
                "month or following invoice"
            ),

            keyword_query=(
                '"activation fee" OR '
                '"activation charge" OR '
                '"one-time charge" OR '
                '"one time charge" OR '
                '"new line fee"'
            ),

            preferred_categories=[
                "activation_fee",
            ],
        )


    # Direct activation-fee wording.

    if contains_any(
        normalized,
        [
            "activation fee",
            "activation charge",
            "charged for activation",
            "fee for activation",
            "fee for activating",
            "new line fee",
        ],
    ):
        return build_analysis(
            query=query,
            intent="activation_fee",

            semantic_terms=(
                "TT&T activation fee, one-time charge for "
                "activating a new mobile line"
            ),

            keyword_query=(
                '"activation fee" OR '
                '"activation charge" OR '
                '"new line fee"'
            ),

            preferred_categories=[
                "activation_fee",
            ],
        )


    # ========================================================
    # 5. BILLING PROMOTION / CREDIT
    # Category: billing_promotion
    # Document: BILL-PROMO-01
    # ========================================================

    promotion_words = [
        "promotion",
        "promotional",
        "promo",
        "discount",
        "bill credit",
        "billing credit",
        "promotional credit",
        "promo credit",
        "credit missing",
        "missing credit",
        "discount missing",
        "promotion missing",
        "promo disappeared",
        "discount disappeared",
        "credit disappeared",
        "expected a credit",
        "didn't get my credit",
        "did not get my credit",
        "monthly credit",
        "no longer getting the credit",
    ]

    if contains_any(
        normalized,
        promotion_words,
    ):
        return build_analysis(
            query=query,
            intent="billing_promotion",

            semantic_terms=(
                "TT&T promotional bill credit, promotion "
                "eligibility, discount, missing monthly credit, "
                "promotional reduction on an invoice"
            ),

            keyword_query=(
                'promotion OR '
                'promotional OR '
                'promo OR '
                'discount OR '
                '"promotional credit" OR '
                '"bill credit" OR '
                '"missing credit"'
            ),

            preferred_categories=[
                "billing_promotion",
            ],
        )


    # ========================================================
    # 6. BILLING TAXES / SURCHARGES
    # Category: billing_tax
    # Document: BILL-TAX-01
    # ========================================================

    tax_words = [
        "tax",
        "taxes",
        "surcharge",
        "surcharges",
        "government fee",
        "government fees",
        "regulatory fee",
        "regulatory fees",
        "tax on my bill",
        "taxes on my bill",
        "extra tax",
        "extra taxes",
        "why is there tax",
        "fees on my bill",
    ]

    if contains_any(
        normalized,
        tax_words,
    ):
        return build_analysis(
            query=query,
            intent="billing_tax",

            semantic_terms=(
                "TT&T invoice taxes, simulated taxes, "
                "government charges, regulatory fees, "
                "billing surcharges and invoice calculation"
            ),

            keyword_query=(
                'tax OR '
                'taxes OR '
                'surcharge OR '
                '"government fee" OR '
                '"regulatory fee"'
            ),

            preferred_categories=[
                "billing_tax",
            ],
        )


    # ========================================================
    # 7. SECURITY / FRAUD / SUSPICIOUS ACTIVITY
    # Category: security
    # Document: SECURITY-01
    # ========================================================

    security_words = [
        "scam",
        "scammer",
        "fraud",
        "fraudulent",
        "phishing",
        "suspicious",
        "hacked",
        "hack",
        "compromised",
        "unauthorized",
        "someone accessed",
        "someone got into",
        "someone logged into",
        "password",
        "one time code",
        "one-time code",
        "otp",
        "authentication code",
        "verification code",
        "transfer pin",
        "account pin",
        "credit card number",
        "full card number",
        "security issue",
        "security problem",
        "identity theft",
        "stole my information",
        "pretending to be ttt",
    ]

    if contains_any(
        normalized,
        security_words,
    ):
        return build_analysis(
            query=query,
            intent="security",

            semantic_terms=(
                "TT&T account security, suspicious activity, "
                "fraud, phishing, unauthorized access, password "
                "protection, authentication codes, transfer PIN "
                "and sensitive customer information"
            ),

            keyword_query=(
                'security OR '
                'fraud OR '
                'scam OR '
                'phishing OR '
                'password OR '
                '"transfer pin" OR '
                '"authentication code" OR '
                'unauthorized'
            ),

            preferred_categories=[
                "security",
            ],
        )


    # ========================================================
    # 8. DATA TROUBLESHOOTING
    #
    # Must remain BEFORE generic network.
    #
    # Category: troubleshooting_data
    # Document: TROUBLE-DATA-01
    # ========================================================

    data_problem_words = [
        "mobile data",
        "cellular data",
        "cell data",
        "data not working",
        "data isn't working",
        "data is not working",
        "internet not working",
        "internet isn't working",
        "no internet",
        "no data",
        "can't use data",
        "cannot use data",
        "cant use data",
        "5g not working",
        "lte not working",
        "5g problem",
        "lte problem",
        "cellular internet",
        "mobile internet",
        "data connection",
        "internet only works on wifi",
        "wifi works but data doesn't",
    ]

    if contains_any(
        normalized,
        data_problem_words,
    ):
        return build_analysis(
            query=query,
            intent="troubleshooting_data",

            semantic_terms=(
                "mobile data troubleshooting, cellular internet "
                "failure, 5G connectivity, LTE connectivity, "
                "mobile internet not working, cellular data "
                "connection troubleshooting"
            ),

            keyword_query=(
                '"mobile data" OR '
                '"cellular data" OR '
                '"data not working" OR '
                '"mobile internet" OR '
                '"5g" OR '
                '"lte"'
            ),

            preferred_categories=[
                "troubleshooting_data",
            ],
        )


    # ========================================================
    # 9. CALL TROUBLESHOOTING
    # Category: troubleshooting_calls
    # Document: TROUBLE-CALL-01
    # ========================================================

    call_problem_words = [
        "calls not working",
        "call not working",
        "can't call",
        "cannot call",
        "cant call",
        "can't make calls",
        "cannot make calls",
        "cant make calls",
        "can't receive calls",
        "cannot receive calls",
        "call failed",
        "calls failing",
        "dropped calls",
        "calls keep dropping",
        "call keeps dropping",
        "phone calls dropping",
        "incoming calls not working",
        "outgoing calls not working",
        "can't dial",
        "cannot dial",
        "voice service not working",
    ]

    if contains_any(
        normalized,
        call_problem_words,
    ):
        return build_analysis(
            query=query,
            intent="troubleshooting_calls",

            semantic_terms=(
                "mobile voice troubleshooting, failed phone calls, "
                "cannot make calls, cannot receive calls, "
                "dropped calls, incoming or outgoing call problems"
            ),

            keyword_query=(
                '"calls not working" OR '
                '"call failed" OR '
                '"dropped calls" OR '
                '"make calls" OR '
                '"receive calls" OR '
                '"voice service"'
            ),

            preferred_categories=[
                "troubleshooting_calls",
            ],
        )


    # ========================================================
    # 10. NETWORK / COVERAGE / OUTAGE
    # Category: network
    # Document: NETWORK-01
    # ========================================================

    network_words = [
        "network",
        "coverage",
        "outage",
        "service outage",
        "network outage",
        "signal",
        "no signal",
        "weak signal",
        "poor signal",
        "no bars",
        "one bar",
        "bars",
        "no service",
        "service down",
        "network down",
        "coverage area",
        "coverage problem",
        "reception",
        "poor reception",
    ]

    if contains_any(
        normalized,
        network_words,
    ):
        return build_analysis(
            query=query,
            intent="network",

            semantic_terms=(
                "TT&T mobile network coverage, service outage, "
                "network availability, signal strength, "
                "poor reception and no-service conditions"
            ),

            keyword_query=(
                'network OR '
                'coverage OR '
                'outage OR '
                '"no service" OR '
                '"no signal" OR '
                '"weak signal" OR '
                'reception'
            ),

            preferred_categories=[
                "network",
            ],
        )


    # ========================================================
    # 11. PAYMENT
    # Category: payment
    # Document: PAYMENT-01
    # ========================================================

    payment_words = [
        "payment",
        "pay my bill",
        "pay bill",
        "payment failed",
        "payment didn't go through",
        "payment did not go through",
        "card declined",
        "declined card",
        "declined payment",
        "autopay",
        "auto pay",
        "automatic payment",
        "payment method",
        "payment problem",
        "make a payment",
        "paid my bill",
    ]

    if contains_any(
        normalized,
        payment_words,
    ):
        return build_analysis(
            query=query,
            intent="payment",

            semantic_terms=(
                "TT&T payment processing, bill payment, "
                "failed payment, declined card payment, "
                "autopay and payment methods"
            ),

            keyword_query=(
                'payment OR '
                '"payment failed" OR '
                '"card declined" OR '
                'autopay OR '
                '"payment method" OR '
                '"pay bill"'
            ),

            preferred_categories=[
                "payment",
            ],
        )


    # ========================================================
    # 12. SIM / ESIM
    # Category: sim_esim
    # Document: SIM-01
    # ========================================================

    sim_words = [
        "sim",
        "sim card",
        "esim",
        "physical sim",
        "digital sim",
        "replace sim",
        "replacement sim",
        "activate sim",
        "sim activation",
        "new sim",
        "switch esim",
        "move esim",
        "esim setup",
        "esim activation",
    ]

    if contains_any(
        normalized,
        sim_words,
    ):
        return build_analysis(
            query=query,
            intent="sim_esim",

            semantic_terms=(
                "TT&T SIM card, eSIM, physical SIM, "
                "SIM activation, SIM replacement and eSIM setup"
            ),

            keyword_query=(
                '"sim card" OR '
                'esim OR '
                '"sim activation" OR '
                '"replace sim" OR '
                '"replacement sim"'
            ),

            preferred_categories=[
                "sim_esim",
            ],
        )


    # ========================================================
    # 13. INTERNATIONAL / ROAMING
    # Category: international
    # Document: INTL-01
    # ========================================================

    international_words = [
        "international",
        "overseas",
        "abroad",
        "roaming",
        "another country",
        "foreign country",
        "outside the us",
        "outside usa",
        "travel internationally",
        "international travel",
        "use my phone abroad",
        "use my phone overseas",
        "international calls",
        "traveling overseas",
        "travelling overseas",
    ]

    if contains_any(
        normalized,
        international_words,
    ):
        return build_analysis(
            query=query,
            intent="international",

            semantic_terms=(
                "TT&T international mobile service, roaming, "
                "travel pass, using a phone overseas or abroad, "
                "international travel and international calling"
            ),

            keyword_query=(
                'international OR '
                'roaming OR '
                'overseas OR '
                'abroad OR '
                '"travel pass" OR '
                '"international calls"'
            ),

            preferred_categories=[
                "international",
            ],
        )


    # ========================================================
    # 14. DEVICE
    # Category: device
    # Document: DEVICE-01
    # ========================================================

    device_service_words = [
        "device installment",
        "phone installment",
        "device payment",
        "phone payment",
        "installment plan",
        "device balance",
        "phone balance",
        "compatible device",
        "device compatible",
        "phone compatible",
        "device compatibility",
        "bring my own device",
        "byod",
        "upgrade device",
        "upgrade phone",
        "new phone",
        "owe on my phone",
        "owe money on my device",
    ]

    if contains_any(
        normalized,
        device_service_words,
    ):
        return build_analysis(
            query=query,
            intent="device",

            semantic_terms=(
                "TT&T mobile device compatibility, BYOD, "
                "device installment, device balance, phone "
                "upgrade and mobile hardware support"
            ),

            keyword_query=(
                '"device installment" OR '
                '"phone installment" OR '
                '"device compatibility" OR '
                '"compatible device" OR '
                'BYOD OR '
                '"device balance"'
            ),

            preferred_categories=[
                "device",
            ],
        )


    # ========================================================
    # 15. PLAN DATA
    #
    # Must remain BEFORE generic plans.
    #
    # Category: plan_data
    # Document: PLAN-DATA-01
    # ========================================================

    plan_data_words = [
        "data allowance",
        "how much data",
        "data limit",
        "data limits",
        "monthly data",
        "data included",
        "included data",
        "run out of data",
        "ran out of data",
        "data usage limit",
        "high speed data",
        "hotspot data",
        "mobile hotspot",
        "hotspot allowance",
    ]

    if contains_any(
        normalized,
        plan_data_words,
    ):
        return build_analysis(
            query=query,
            intent="plan_data",

            semantic_terms=(
                "TT&T plan data allowance, included monthly "
                "mobile data, hotspot data, high-speed data "
                "limits and data usage policies"
            ),

            keyword_query=(
                '"data allowance" OR '
                '"data limit" OR '
                '"included data" OR '
                '"hotspot data" OR '
                '"high speed data"'
            ),

            preferred_categories=[
                "plan_data",
            ],
        )


    # ========================================================
    # 16. PLANS / PLAN CATALOG
    # Category: plans
    # Document: PLAN-CATALOG-01
    # ========================================================

    plan_words = [
        "plans",
        "plan options",
        "which plan",
        "best plan",
        "available plans",
        "plan price",
        "plan prices",
        "how much is the plan",
        "monthly plan",
        "unlimited plan",
        "change my plan",
        "switch my plan",
        "upgrade my plan",
        "downgrade my plan",
        "mobile plan",
        "service plan",
    ]

    if contains_any(
        normalized,
        plan_words,
    ):
        return build_analysis(
            query=query,
            intent="plans",

            semantic_terms=(
                "TT&T mobile plan catalog, available service "
                "plans, monthly plan pricing, unlimited plans, "
                "choosing or changing a mobile plan"
            ),

            keyword_query=(
                '"mobile plan" OR '
                '"plan options" OR '
                '"available plans" OR '
                '"unlimited plan" OR '
                '"plan price" OR '
                '"change plan"'
            ),

            preferred_categories=[
                "plans",
            ],
        )


    # ========================================================
    # 17. NEW CONNECTION / JOINING
    #
    # IMPORTANT:
    # Bare "new line" is NOT sufficient.
    # Activation-fee questions often contain "new line".
    #
    # Category: new_connection
    # Document: JOIN-01
    # ========================================================

    new_connection_words = [
        "join ttt",
        "sign up",
        "signup",
        "become a customer",
        "new customer",
        "new connection",
        "start service",
        "start new service",
        "open service",
        "get ttt service",
        "switch to ttt",
        "want a new line",
        "need a new line",
        "add a new line",
        "get a new line",
    ]

    if contains_any(
        normalized,
        new_connection_words,
    ):
        return build_analysis(
            query=query,
            intent="new_connection",

            semantic_terms=(
                "join TT&T, become a new customer, "
                "start new mobile service, request a new "
                "connection, add a mobile line"
            ),

            keyword_query=(
                '"new connection" OR '
                '"start service" OR '
                '"join ttt" OR '
                '"sign up" OR '
                '"add new line"'
            ),

            preferred_categories=[
                "new_connection",
            ],
        )


    # ========================================================
    # 18. ACCOUNT
    # Category: account
    # Document: ACCOUNT-01
    # ========================================================

    account_words = [
        "my account",
        "account information",
        "account details",
        "account status",
        "account profile",
        "update my account",
        "change my address",
        "update address",
        "change my email",
        "update email",
        "account owner",
        "account access",
        "my profile",
    ]

    if contains_any(
        normalized,
        account_words,
    ):
        return build_analysis(
            query=query,
            intent="account",

            semantic_terms=(
                "TT&T customer account information, account "
                "profile, account status, customer details "
                "and account management"
            ),

            keyword_query=(
                '"account information" OR '
                '"account details" OR '
                '"account status" OR '
                '"account profile" OR '
                '"my account"'
            ),

            preferred_categories=[
                "account",
            ],
        )


    # ========================================================
    # 19. SUPPORT / ESCALATION
    # Category: support
    # Document: SUPPORT-01
    # ========================================================

    support_words = [
        "contact support",
        "customer support",
        "customer service",
        "talk to support",
        "talk to someone",
        "talk to a person",
        "talk to an agent",
        "human agent",
        "real person",
        "representative",
        "support agent",
        "open a ticket",
        "create a ticket",
        "support ticket",
        "escalate",
        "escalation",
        "need help from someone",
    ]

    if contains_any(
        normalized,
        support_words,
    ):
        return build_analysis(
            query=query,
            intent="support",

            semantic_terms=(
                "TT&T customer support, support ticket, "
                "human customer-service agent, escalation and "
                "customer-service representative"
            ),

            keyword_query=(
                '"customer support" OR '
                '"support ticket" OR '
                '"human agent" OR '
                'representative OR '
                'escalation'
            ),

            preferred_categories=[
                "support",
            ],
        )


    # ========================================================
    # 20. FAQ / DEMO CAPABILITIES
    # Category: faq
    # Document: FAQ-01
    # ========================================================

    faq_words = [
        "what is ttt",
        "what is tt&t",
        "what can you do",
        "what can this chatbot do",
        "what can the chatbot do",
        "what can the assistant do",
        "how can you help",
        "what do you support",
        "what services can you help with",
        "demo limitations",
        "demo limits",
    ]

    if contains_any(
        normalized,
        faq_words,
    ):
        return build_analysis(
            query=query,
            intent="faq",

            semantic_terms=(
                "TT&T customer support FAQ, chatbot capabilities, "
                "supported customer-service questions, "
                "demonstration boundaries and limitations"
            ),

            keyword_query=(
                'faq OR '
                '"chatbot capabilities" OR '
                '"customer support" OR '
                '"demo limitations"'
            ),

            preferred_categories=[
                "faq",
            ],
        )


    # ========================================================
    # FALLBACK
    # ========================================================

    # Unknown queries still go through:
    #
    #   BGE vector search
    #   PostgreSQL FTS
    #   RRF
    #   reranker
    #
    # They simply receive no metadata-category boost.

    return {
        "intent": "general",
        "original_query": query,
        "semantic_query": query,
        "keyword_query": query,
        "preferred_categories": [],
    }

