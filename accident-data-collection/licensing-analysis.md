# Licensing Analysis: Can We Use This Data to Train a Commercial Foundation Model?

> **Investigated**: 16 April 2026
> **Question**: Do the CC-BY 4.0 licences on Australian government traffic data permit using it to train a foundation model for commercial use?

---

## Short Answer

**Yes — CC-BY 4.0 permits commercial AI training, and none of the API terms of service add AI-specific restrictions.** Creative Commons confirmed this explicitly in May 2025 guidance. The main obligation is attribution in your model card/documentation.

There are nuances around Australian copyright law (no TDM exception), but these are irrelevant when the data is already licensed to you under CC-BY 4.0. You have the licence — that's the whole point.

---

## Per-Source Verdict

| Source | Licence | Commercial AI Training? | API ToS Restrictions on AI? | Verdict |
|--------|---------|------------------------|----------------------------|---------|
| **TfNSW** | CC BY 4.0 International | **Permitted** | None found | **GO** |
| **DTP Victoria** (ex-VicRoads) | CC BY 4.0 International | **Permitted** | None found | **GO** |
| **QLDTraffic** | CC BY 4.0 Australia ("AU")* | **Permitted** | None found | **GO** |
| **TomTom** | Proprietary (free tier) | **Check ToS** | Likely restricted | **CAUTION** |
| **HERE** | Proprietary (free tier) | **Check ToS** | Likely restricted | **CAUTION** |
| **jxeeno GitHub archive** | Derived from CC-BY 4.0 TfNSW data | **Permitted** (same as TfNSW) | N/A | **GO** |
| **Mendeley Sydney GMA dataset** | CC-BY 4.0 | **Permitted** | N/A | **GO** |

\* The QLDTraffic API specification v1.10 (19 Feb 2025) stamps the license as
"Creative Commons Attribution 4.0 Australia" with URL
`creativecommons.org/licenses/by/4.0/au/`. CC BY 4.0 is jurisdiction-neutral
by design (CC moved away from localised ports after CC 3.0), and the `/au/`
URL redirects to the international 4.0 terms. The substantive permissions
— share, adapt, commercial use, AI training — are identical. The only
practical difference is the attribution string, which should cite the State
of Queensland (Department of Transport and Main Roads) rather than a
global CC BY attribution.

**Recommendation**: Stick to the government CC BY 4.0 sources for training data. Avoid TomTom/HERE data in the training set unless their commercial terms explicitly permit AI training — their free-tier ToS likely do not.

---

## CC-BY 4.0 and AI Training — The Law

### Creative Commons' Official Position (May 2025)

Creative Commons published two authoritative documents in May 2025:

1. **["Using CC-licensed Works for AI Training"](https://creativecommons.org/wp-content/uploads/2025/05/Using-CC-licensed-Works-for-AI-Training.pdf)** — guidance document
2. **["Understanding CC Licenses and AI Training: A Legal Primer"](https://creativecommons.org/2025/05/15/understanding-cc-licenses-and-ai-training-a-legal-primer/)** — legal analysis

Key findings from these documents:

- **CC licences do not restrict reuse to particular types of reuse or technologies.** No special permission is needed to use CC-licensed content for AI training.
- **CC-BY 4.0 specifically** authorises reproduction, redistribution, communication to the public, and adaptation — all for any purpose including commercial.
- **The NonCommercial (NC) and NoDerivatives (ND) restrictions** are the problematic ones for AI. CC-BY 4.0 contains **neither**.
- Attribution (BY) and ShareAlike (SA) conditions are triggered only when **works or adaptations are publicly shared** — not during the internal act of training.

### Is a Trained Model a "Derivative Work" of Training Data?

This is the key theoretical question, and the answer strongly favours your case:

- For **factual/structured data** (GPS coordinates, timestamps, incident categories), a trained model does not "memorise" or "reproduce" the training data. The model internalises statistical patterns, not individual records.
- The US Copyright Office's May 2025 report noted that model weights could be derivative works only where they demonstrate "memorisation" of **protected expression** — this applies to novels and artwork, not traffic incident timestamps.
- Even if model weights were considered an "adaptation" of the data, **CC-BY 4.0 permits adaptation** including for commercial purposes. The only obligation would be attribution.

### What Attribution Is Required?

Creative Commons recommends:
- **Minimum**: A link to the data source in the model card or documentation
- **For RAG systems**: Attribution tied to particular outputs (if applicable)

**Practical approach**: Include this in your model card:

> **Training Data Attribution**
>
> This model was trained using traffic incident data from the following sources, licensed under Creative Commons Attribution 4.0 International (CC-BY 4.0):
> - Transport for NSW Open Data Hub (https://opendata.transport.nsw.gov.au/) — Crown copyright, State of New South Wales
> - Department of Transport and Planning, Victoria (https://data.vic.gov.au/) — Crown copyright, State of Victoria
> - Queensland Department of Transport and Main Roads (https://data.qld.gov.au/) — Crown copyright, State of Queensland

---

## Australian Copyright Law — Why the TDM Debate Doesn't Affect You

### The Situation

On 26 October 2025, the Australian Government **rejected** introducing a text and data mining (TDM) exception to the Copyright Act 1968. This means there is no blanket statutory right to use copyrighted material for AI training in Australia.

Australia's existing fair dealing exceptions (research/study, news reporting, criticism/review, parody/satire, judicial proceedings) **do not cover AI training**. Legal commentators are unanimous on this.

### Why This Doesn't Matter for Your Case

The TDM debate is about **unlicensed content** — scraping copyrighted text/images from the web without permission. Your situation is fundamentally different:

- You have an **explicit licence** (CC-BY 4.0) that grants you the right to reproduce, adapt, and commercially use the data
- The Australian Government's position is: "get a licence before using copyrighted material for AI training." **You have the licence.**
- CC-BY 4.0 is irrevocable (Section 2(b)(1)) — data obtained under the licence remains licensed even if the licensor later changes terms for new users

You are in the compliant lane that the government's own framework contemplates.

### Additional Factor: Factual Data Has Weak Copyright

Australia does not have a sui generis database right (unlike the EU). The individual data points — coordinates, timestamps, incident categories — are facts, not creative expression. Even the "sweat of the brow" doctrine (which Australia still applies, unlike the US) only protects the effort of *compiling* the database, not the facts themselves. And regardless, the CC-BY 4.0 licence covers the compilation too.

---

## Specific API Terms of Service

### TfNSW Open Data Hub Terms (September 2024)

Reviewed the [TfNSW Open Data Portal Terms PDF](https://opendata.transport.nsw.gov.au/sites/default/files/2024-09/TfNSW-Open-Data-Portal-Terms.pdf) and [Open Data Policy (2025)](https://www.transport.nsw.gov.au/system/files/media/documents/2025/open-data-policy.pdf):

- Data described as available "for any purpose"
- Must not imply TfNSW endorsement or sponsorship of your product
- Must attribute TfNSW as the data source
- Must respect API rate limits
- **No mention of AI, machine learning, or model training restrictions**

### DataVic Access Policy (Victoria)

Reviewed the [DataVic Access Policy](https://www.data.vic.gov.au/datavic-access-policy):

- CC-BY 4.0 is the default and "least restrictive licence"
- Policy "encourages access to Crown copyright on the least restrictive terms appropriate"
- **No mention of AI or ML restrictions**

### Queensland Open Data Strategy 2025–2029

Reviewed the [QLD Open Data Strategy](https://www.oic.qld.gov.au/publications/policies/open-data-strategy):

- Explicitly states that "'non-commercial' restrictions that would prevent 'commercial' use, or restrictions of use for certain purposes, **are not allowed**"
- This is the most explicitly permissive of the three — actively prohibiting *any* use-case restrictions

---

## International Context

| Jurisdiction | TDM/AI Exception? | Effect on CC-BY 4.0 data |
|---|---|---|
| **Australia** | No. Rejected Oct 2025. | Irrelevant — you have a licence |
| **EU** | Yes. DSM Directive Art. 3 & 4. AI Act Art. 53. | CC-BY 4.0 does not opt out of TDM |
| **UK** | Limited. Non-commercial only (s.29A). | CC-BY 4.0 provides commercial permission |
| **US** | No statute. Fair use (case-by-case). | CC-BY 4.0 provides explicit permission |
| **Japan** | Yes. Broad exception (Art. 30-4, 2018). | Compliant regardless |

In every major jurisdiction, using CC-BY 4.0 data for commercial AI training is permissible.

---

## Risk Assessment

| Risk | Level | Notes |
|------|-------|-------|
| CC-BY 4.0 prohibits AI training | **None** | Explicitly confirmed as permitted by CC (May 2025) |
| API ToS restrict AI use | **Low** | No AI restrictions found in any government API terms |
| Model weights as derivative work | **Low** | Very weak argument for factual/structured data |
| Future CAIRG licensing framework | **Low-Medium** | Under development; unlikely to retroactively affect CC-BY 4.0 data already obtained |
| API terms changed in future | **Low** | CC-BY 4.0 is irrevocable for already-obtained data |
| Reputational risk | **Low** | Using government open data for innovation is exactly the intended purpose |
| TomTom/HERE data in training set | **Medium-High** | Proprietary terms likely restrict AI training — exclude from training data |

---

## Recommended Actions

### Do Now

1. **Screenshot and archive the licence terms** from each data portal as they exist today
2. **Save copies of**: TfNSW Open Data Hub Terms PDF, DataVic Access Policy, QLD Open Data Strategy
3. **Exclude TomTom and HERE data from training datasets** — use them only for validation/comparison, not model training, unless their commercial terms explicitly permit AI use

### Include in Model Documentation

4. **Add attribution** in model card (template above)
5. **Do not** use government logos or imply endorsement
6. **Document data provenance** — when each dataset was accessed, which API version, under which licence terms

### Optional but Recommended

7. **Get a brief legal opinion** from a copyright lawyer familiar with AI (firms with published expertise: MinterEllison, Bird & Bird, Ashurst, King & Wood Mallesons) — this provides additional protection and is useful for investor/partner due diligence
8. **Monitor CAIRG developments** — the Copyright and AI Reference Group may propose new frameworks that could affect future data collection (but not data already obtained)

---

## Key Legal Sources

- [Using CC-licensed Works for AI Training (Creative Commons, May 2025)](https://creativecommons.org/wp-content/uploads/2025/05/Using-CC-licensed-Works-for-AI-Training.pdf)
- [Understanding CC Licenses and AI Training: A Legal Primer (Creative Commons, May 2025)](https://creativecommons.org/2025/05/15/understanding-cc-licenses-and-ai-training-a-legal-primer/)
- [Australia Rejects TDM Exception (Attorney-General's Dept, Oct 2025)](https://ministers.ag.gov.au/media-centre/albanese-government-ensure-australia-prepared-future-copyright-challenges-emerging-ai-26-10-2025)
- [CAIRG (Copyright and AI Reference Group)](https://www.ag.gov.au/rights-and-protections/copyright/copyright-and-artificial-intelligence-reference-group-cairg)
- [Productivity Commission Final Report (Dec 2025)](https://www.copyright.com.au/2025/12/productivity-commission-reports-released/)
- [Australian copyright law and AI (Kluwer Copyright Blog)](https://legalblogs.wolterskluwer.com/copyright-blog/australian-copyright-law-is-inhibiting-the-development-of-ai-what-options-does-the-australian-government-have/)
- [3 Key Takeaways from Australia's AI Copyright Reform (Bird & Bird)](https://www.twobirds.com/en/insights/2025/australia/3-key-takeaways-from-australia%E2%80%99s-latest-ai-copyright-law-reform-announcement)
- [TfNSW Open Data Portal Terms (PDF, Sep 2024)](https://opendata.transport.nsw.gov.au/sites/default/files/2024-09/TfNSW-Open-Data-Portal-Terms.pdf)
- [DataVic Access Policy](https://www.data.vic.gov.au/datavic-access-policy)
- [QLD Open Data Strategy 2025–2029](https://www.oic.qld.gov.au/publications/policies/open-data-strategy)
