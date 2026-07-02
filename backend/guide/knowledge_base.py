GUIDE_ENTRIES = [
    {
        "id": "start-trading",
        "keywords": ["start trading", "begin", "beginner", "how to invest", "first time", "getting started"],
        "title": "How to Start Trading in NEPSE",
        "content": [
            "Step 1: Open a Demat Account — Visit any Depository Participant (bank or broker) with your citizenship certificate, passport photo, and bank details. You'll receive a 16-digit BOID number.",
            "Step 2: Register on MeroShare — Go to meroshare.cdsc.com.np and register using your BOID. This lets you apply for IPOs and view your portfolio.",
            "Step 3: Choose a Licensed Broker — Select from 50+ SEBON-licensed brokers. Visit sebon.gov.np/intermediaries/stock-brokers for the full list.",
            "Step 4: Open a Trading Account — Submit KYC documents to your broker. They will provide TMS (Trading Management System) login credentials.",
            "Step 5: Fund Your Account — Transfer funds to your broker's pool account via internet banking or ConnectIPS.",
            "Step 6: Place Your First Order — Log in to TMS, search for the stock symbol (e.g., NABIL), enter quantity (Kitta) and price, and submit. Market hours: 11 AM – 3 PM, Sunday to Thursday.",
        ],
        "sources": [
            {"name": "SEBON Investor Handbook", "url": "https://www.sebon.gov.np"},
            {"name": "CDSC FAQ", "url": "https://cdsc.com.np"},
            {"name": "NEPSE Official", "url": "https://nepalstock.com.np"},
        ],
    },
    {
        "id": "demat-account",
        "keywords": ["demat", "demat account", "dematerialized", "open demat", "bo account", "beneficial owner"],
        "title": "How to Open a Demat Account",
        "content": [
            "A Demat (Dematerialized) account holds your shares electronically. It is mandatory for trading in NEPSE.",
            "Where to open: Any Depository Participant (DP) — commercial banks, stock brokers, or merchant bankers registered with CDSC.",
            "Required documents: Citizenship certificate (original + photocopy), 2 passport-size photos, bank account details, PAN card (if applicable).",
            "Process: Fill the account opening form → Submit KYC documents → In-person or video verification → Account created in 1-3 business days.",
            "You will receive a 16-digit BOID (Beneficiary Owner ID) — this is your unique Demat account number.",
            "Cost: Opening fee ~Rs. 50-150. Annual maintenance ~Rs. 100.",
            "You can open up to 2 Demat accounts in Nepal.",
        ],
        "sources": [
            {"name": "CDSC Nepal — Demat Account Guide", "url": "https://cdsc.com.np/accountopening"},
            {"name": "SEBON Investor Handbook", "url": "https://www.sebon.gov.np"},
        ],
    },
    {
        "id": "broker-account",
        "keywords": ["broker", "broker account", "broker list", "find broker", "trading account", "tms", "register broker", "open broker account", "choose broker", "near me"],
        "title": "How to Open a Broker (Trading) Account",
        "content": [
            "A broker account (Trading Account) lets you buy and sell shares on NEPSE. You must go through a SEBON-licensed broker.",
            "Step 1: Choose a broker from the SEBON list at sebon.gov.np/intermediaries/stock-brokers. Consider location, online KYC availability, and service quality.",
            "Step 2: Visit the broker's office or apply online. Submit citizenship, passport photo, Demat BOID number, and bank details.",
            "Step 3: After verification, the broker provides your TMS (Trading Management System) username and password.",
            "TMS URL format: https://tms<broker-number>.nepsetms.com.np (e.g., tms49.nepsetms.com.np for broker 49).",
            "There are no charges for opening a broker account — it's free.",
            "Brokers also provide collateral loans (typically 1:4 ratio against your shares).",
        ],
        "sources": [
            {"name": "SEBON — List of Stock Brokers", "url": "https://sebon.gov.np/intermediaries/stock-brokers"},
            {"name": "NEPSE Official", "url": "https://nepalstock.com.np"},
        ],
    },
    {
        "id": "meroshare",
        "keywords": ["meroshare", "mero share", "ipo", "fpo", "right share", "cdsc", "portfolio"],
        "title": "What is MeroShare and How to Use It",
        "content": [
            "MeroShare is CDSC's online portal for managing your Demat account, applying for IPOs/FPOs, viewing holdings, and transferring shares.",
            "Website: meroshare.cdsc.com.np (also available as a mobile app).",
            "Registration: Go to meroshare.cdsc.com.np → Click Register → Select your DP (bank/broker where you opened Demat) → Enter BOID and personal details → Set username/password.",
            "Key features: Apply for IPOs/FPOs/Rights, check allotment results, view portfolio, transfer shares via E-DIS, download account statements.",
            "Note: MeroShare does NOT support direct buying/selling of shares. Trading is done through your broker's TMS.",
        ],
        "sources": [
            {"name": "CDSC MeroShare", "url": "https://meroshare.cdsc.com.np"},
            {"name": "CDSC FAQ", "url": "https://cdsc.com.np"},
        ],
    },
    {
        "id": "trading-hours",
        "keywords": ["trading hours", "market hours", "nepse time", "when to trade", "holidays", "market open"],
        "title": "NEPSE Trading Hours & Holidays",
        "content": [
            "Trading sessions: Sunday to Thursday, 11:00 AM to 3:00 PM (Nepal time).",
            "Friday and Saturday: Market closed (weekly holidays).",
            "Public holidays: NEPSE follows Nepal Government's public holiday calendar.",
            "Pre-open session: 10:30 AM – 11:00 AM (order placement without matching).",
            "Continuous trading: 11:00 AM – 3:00 PM (orders match in real-time).",
            "Settlement cycle: T+2 (trade date + 2 business days).",
        ],
        "sources": [
            {"name": "NEPSE Official — Trading Hours", "url": "https://nepalstock.com.np"},
        ],
    },
    {
        "id": "charges-fees",
        "keywords": ["charges", "fees", "commission", "broker charge", "tax", "capital gain", "sebon fee", "cdsc fee"],
        "title": "Trading Charges & Fees",
        "content": [
            "Broker commission: 0.4% (buy) + 0.4% (sell) of transaction value (maximum). Many brokers offer discounted rates.",
            "SEBON fee: 0.015% of transaction value.",
            "CDSC fee: Rs. 25 per transaction per stock.",
            "Capital Gains Tax: 5% for individual holders holding less than 1 year, 2.5% for holdings over 1 year. (For listed shares.)",
            "Dividend Tax: 5% on cash dividends, 5% on bonus shares (at time of sale).",
            "TMS/DP charges: Annual maintenance ~Rs. 100-200 depending on the DP.",
        ],
        "sources": [
            {"name": "SEBON — Securities Tax Directives", "url": "https://www.sebon.gov.np"},
            {"name": "Inland Revenue Department Nepal", "url": "https://ird.gov.np"},
        ],
    },
    {
        "id": "ipo-application",
        "keywords": ["ipo", "fpo", "apply ipo", "public issue", "initial public offering", "allotment", "ipo result"],
        "title": "How to Apply for an IPO in Nepal",
        "content": [
            "Step 1: Ensure you have a Demat account and MeroShare registration.",
            "Step 2: Log in to MeroShare and click 'Apply for IPO' under 'My Application'.",
            "Step 3: Select the issue, enter the number of shares (minimum 10 kitta), and submit. Ensure sufficient funds are in your linked ASBA bank account.",
            "Step 4: Check allotment results on MeroShare under 'My Application' → 'View Allotment'.",
            "Minimum application: 10 shares (kitta). Maximum varies by issue.",
            "Refunds: Unused application money is automatically refunded to your bank account within 7-14 days of allotment.",
            "ASBA (Application Supported by Blocked Amount): Your bank blocks the application amount; it's not debited unless shares are allotted.",
        ],
        "sources": [
            {"name": "CDSC MeroShare Guide", "url": "https://meroshare.cdsc.com.np"},
            {"name": "SEBON — IPO Process", "url": "https://www.sebon.gov.np"},
        ],
    },
    {
        "id": "investor-protection",
        "keywords": ["safety", "scam", "fraud", "investor protection", "sebon complaint", "grievance", "regulation"],
        "title": "Investor Protection & Safety",
        "content": [
            "SEBON (Securities Board of Nepal) is the regulatory authority. File complaints via gunaso@sebon.gov.np or call toll-free: 1660 01 44433.",
            "Never share your TMS password, MeroShare password, or OTP with anyone.",
            "Only trade through SEBON-licensed brokers. Verify broker license at sebon.gov.np.",
            "Be cautious of 'guaranteed returns' schemes and social media tips promising quick profits.",
            "The Investor Protection Fund (IPF) provides compensation in case of broker default (up to NPR 500,000 per investor).",
            "Report suspicious activities: SEBON Grievance Hotline: +977-01-5254076.",
            "Always use the official MeroShare URL (meroshare.cdsc.com.np). Beware of phishing sites.",
        ],
        "sources": [
            {"name": "SEBON — Grievance Handling", "url": "https://www.sebon.gov.np"},
            {"name": "SEBON Toll-Free: 1660 01 44433", "url": "tel:16600144433"},
        ],
    },
    {
        "id": "edis-transfer",
        "keywords": ["edis", "e-dis", "transfer shares", "sell shares", "delivery", "share transfer"],
        "title": "How to Transfer Shares via E-DIS",
        "content": [
            "E-DIS (Electronic Delivery Instruction Slip) is CDSC's system to transfer shares from your Demat account to your broker for selling.",
            "Step 1: Log in to MeroShare → go to 'My Portfolio' → select the stock you want to sell.",
            "Step 2: Click 'E-DIS' and enter: broker number, quantity, and scrip. This sends your shares to the broker's clearing account.",
            "Step 3: Once the shares are credited to the broker, you can place a sell order through TMS.",
            "Shares are transferred within T+2 days after sale settlement.",
            "E-DIS is free and can be done anytime (not just during market hours).",
        ],
        "sources": [
            {"name": "CDSC — E-DIS Guide", "url": "https://cdsc.com.np"},
        ],
    },
    {
        "id": "dividend",
        "keywords": ["dividend", "bonus share", "cash dividend", "stock dividend", "right share", "corporate action"],
        "title": "Dividends, Bonus Shares & Rights Issue",
        "content": [
            "Cash Dividend: Company distributes profit as cash per share. Tax: 5% deducted at source.",
            "Bonus Share: Company issues additional shares to existing shareholders. Tax: 5% payable at time of selling bonus shares.",
            "Rights Issue: Existing shareholders can buy additional shares at a discounted price. Apply via MeroShare within the specified period.",
            "Dividend announcement schedule: Companies typically announce dividends during their AGM (usually Oct-Dec for fiscal year ending July).",
            "Check proposed dividends on ShareSansar (sharesansar.com) or NEPSE website.",
            "Dividends are credited directly to your Demat account (bonus shares) or bank account (cash dividend).",
        ],
        "sources": [
            {"name": "ShareSansar — Dividends", "url": "https://www.sharesansar.com/dividend"},
            {"name": "SEBON — Corporate Actions", "url": "https://www.sebon.gov.np"},
        ],
    },
    {
        "id": "c-asba",
        "keywords": ["c-asba", "asba", "blocked amount", "application supported by blocked amount", "ipo payment", "how to pay ipo", "fund block"],
        "title": "What is C-ASBA and How Does It Work",
        "content": [
            "C-ASBA (Blocking Amount Facility) is a system where your bank blocks the application amount when you apply for an IPO/FPO via MeroShare. The money is NOT debited — it's reserved until allotment.",
            "How it works: You select a C-ASBA-enabled bank account in MeroShare → the application amount is blocked → if shares are not allotted, the block is released (usually within 7-14 days) → if allotted, the amount is debited for the allotted shares and the rest is released.",
            "Eligibility: You need a bank account with C-ASBA facility. Most Nepali commercial banks support C-ASBA.",
            "How to link: Register your bank account in MeroShare under 'My ASBA' → enter account number → verify via OTP/RP (Reference Profile).",
            "No manual payment needed: Unlike older systems, you don't need to deposit money to a separate pool account. The block happens automatically.",
            "C-ASBA is mandatory for all public issue applications in Nepal as of 2025.",
        ],
        "sources": [
            {"name": "CDSC — C-ASBA FAQ", "url": "https://cdsc.com.np"},
            {"name": "SEBON Directive on C-ASBA", "url": "https://www.sebon.gov.np"},
        ],
    },
    {
        "id": "check-allotment",
        "keywords": ["check allotment", "allotment result", "ipo result", "allotment status", "view allotment", "how to check allotment", "allotted"],
        "title": "How to Check IPO/FPO Allotment Results",
        "content": [
            "Method 1 — MeroShare: Log in → 'My Application' → 'View My Application' → See status. Allotted shares appear in your Demat portfolio.",
            "Method 2 — SMS: Banks send SMS notifications when shares are allotted to your account.",
            "Method 3 — CDSC Website: Visit cdsc.com.np → Results Section → Search by BOID number.",
            "Method 4 — ShareSansar: sharesansar.com publishes allotment results for all issues.",
            "Timeline: Allotment results are published 7-30 days after the issue close date. Rights issues may take longer.",
            "What to check: Number of shares allotted (usually 10 kitta minimum), refund amount (unblocked by your bank), and credit date to your Demat account.",
            "If not allotted: Your C-ASBA block is automatically released. You can reapply for the next issue.",
        ],
        "sources": [
            {"name": "CDSC MeroShare", "url": "https://meroshare.cdsc.com.np"},
            {"name": "ShareSansar — Allotment", "url": "https://www.sharesansar.com/allotment"},
        ],
    },
    {
        "id": "sell-after-listing",
        "keywords": ["sell after listing", "sell ipo shares", "listing day", "how to sell ipo", "first day listing", "unlisted shares", "ipo listing sell"],
        "title": "How to Sell IPO Shares After Listing",
        "content": [
            "Before listing: IPO shares are credited to your Demat account before the listing date. Check MeroShare → 'My Portfolio' to confirm.",
            "Listing day: The company is listed on NEPSE. You can place sell orders through your broker's TMS or trading platform.",
            "Price discovery: On listing day, the opening price may differ from the IPO price. Prices can be volatile in the first few days.",
            "Sell process: Log in to TMS → Place sell order → Enter quantity and price → Submit. Shares are delivered via E-DIS automatically.",
            "Settlement: Funds from the sale are credited to your broker account after T+2 settlement. You can then withdraw to your bank.",
            "Lock-in period: Some IPO shares (e.g., promoter quota, employee quota) may have a lock-in period. General public shares have no lock-in.",
            "Holding period and tax: Sell within 1 year → 5% capital gains tax. Hold over 1 year → 2.5% capital gains tax.",
        ],
        "sources": [
            {"name": "NEPSE — Listing Process", "url": "https://nepalstock.com.np"},
            {"name": "SEBON — Capital Gains Tax", "url": "https://www.sebon.gov.np"},
        ],
    },
    {
        "id": "ipo-vs-fpo-rights",
        "keywords": ["ipo vs fpo", "fpo vs rights", "ipo difference", "public issue types", "rights issue vs ipo", "bonus vs rights", "share types"],
        "title": "IPO vs FPO vs Rights Issue vs Bonus Shares",
        "content": [
            "IPO (Initial Public Offering): A private company offers shares to the general public for the first time to get listed on NEPSE. Open to all investors with a Demat account.",
            "FPO (Further Public Offering): An already-listed company issues additional shares to the public to raise more capital. Similar process to IPO.",
            "Rights Issue: Existing shareholders can buy new shares at a discounted price (usually 15-30% below market price) in proportion to their current holdings. Not open to new investors.",
            "Bonus Shares: Free shares from a company's retained earnings, distributed proportionally to existing shareholders. No payment required.",
            "Key difference: IPO/FPO raises new capital from the public. Rights issue raises capital from existing shareholders. Bonus shares are profit distribution, not capital raising.",
            "Tax implications: IPO/FPO — no immediate tax. Rights — no tax at application. Bonus — 5% tax payable when bonus shares are sold.",
            "Application process: IPO/FPO — apply via MeroShare. Rights — apply via MeroShare within the specified period. Bonus — automatically credited to Demat account.",
        ],
        "sources": [
            {"name": "SEBON — Securities Issuance", "url": "https://www.sebon.gov.np"},
            {"name": "CDSC MeroShare", "url": "https://meroshare.cdsc.com.np"},
        ],
    },
]


def find_guide_entry(query: str) -> dict | None:
    query_lower = query.lower().strip()

    best = None
    best_score = 0

    for entry in GUIDE_ENTRIES:
        score = 0
        for kw in entry["keywords"]:
            if kw in query_lower:
                score += len(kw.split()) * 2
            else:
                for word in kw.split():
                    if word in query_lower:
                        score += 1
        if score > best_score:
            best_score = score
            best = entry

    return best if best_score >= 3 else None


def get_popular_entries() -> list[dict]:
    return [
        {"id": e["id"], "title": e["title"]}
        for e in GUIDE_ENTRIES[:5]
    ]
