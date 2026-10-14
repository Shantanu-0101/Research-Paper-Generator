"""
The 26 patterns of AI-generated writing, structured as data.
Based on Wikipedia's "Signs of AI writing" and the blader/humanizer project.
"""

from dataclasses import dataclass, field


@dataclass
class Pattern:
    number: int
    name: str
    category: str
    description: str
    watch_for: str
    problem: str
    before: str = ""
    after: str = ""
    weak_alone: bool = False


PATTERNS: list[Pattern] = [
    # ── A. Staging instead of stating ──────────────────────────────────────────
    Pattern(
        number=1,
        name="Not X but Y",
        category="staging",
        description="The negative half names something no one claimed, so the positive half sounds larger.",
        watch_for="not X but Y; not just, not only, or not merely X, but Y; it's not X, it's Y; the reversed form X rather than Y; the same contrast split across sentences; a clipped negative tail.",
        problem="It adds weight without adding a claim. State the point directly. Keep a contrast only when the negative half corrects a belief the reader actually holds, or when both halves carry information.",
        before="It's not just about the beat riding under the vocals; it's part of the aggression and atmosphere.",
        after="The heavy beat adds to the aggressive tone.",
    ),
    Pattern(
        number=2,
        name="One-line closers and dramatic fragments",
        category="staging",
        description="A one-sentence paragraph that restates the paragraph before it.",
        watch_for="a one-sentence paragraph that restates the paragraph before it; 'That is the real win.'; 'Read that again.'; 'Let that sink in.'; the same closer after several sections; a row of fragments; one word in ALL CAPS or with periods between words.",
        problem="The line asks the reader to pause on a claim instead of adding to it. Cut a closer that repeats. Merge a row of fragments into a sentence with a specific claim.",
        before="Caching cuts repeat work.\n\nThat is the real win.",
        after="Caching cuts repeat work.",
    ),
    Pattern(
        number=3,
        name="Sayings that sound deep",
        category="staging",
        description="An ordinary point is dressed as a hidden truth or an aphorism.",
        watch_for="the real question is, at its core, in reality, what really matters, fundamentally, the deeper issue, the heart of the matter, X is the Y of Z, X becomes a trap, the language of, the currency of, the architecture of.",
        problem="The dressing adds no detail. Replace the saying with the specific claim.",
        before="The real question is whether teams can adapt. At its core, what really matters is organizational readiness.",
        after="The question is whether teams can adapt. That mostly depends on whether the organization is ready to change its habits.",
    ),
    Pattern(
        number=4,
        name="Staged run-up before the point",
        category="staging",
        description="The writer announces the point or stages a moment of candor instead of making the point.",
        watch_for="Let's dive in, let's explore, let's break this down, here's what you need to know, now let's look at, without further ado, heads up, quick note, Honestly?, Look, Here's the thing, The thing is, Let's be honest, Real talk.",
        problem="Remove the run-up, not just its tone. 'Honestly' or 'look' inside a casual sentence is ordinary; the tell is the standalone opener before a routine claim.",
        before="Let's dive into how caching works in Next.js. Here's what you need to know.",
        after="Next.js caches data at multiple layers, including request memoization, the data cache, and the router cache.",
    ),
    Pattern(
        number=5,
        name="Arguing with no one",
        category="staging",
        description="The text answers an objection or rejects an option that appears nowhere else.",
        watch_for="This isn't (mainly) about, I'm not saying, To be clear, Don't get me wrong, This is not to say, Some might say... but, A tempting approach would be, One might be tempted to, An obvious approach would be, You might think... but, It would be easy to just.",
        problem="Remove the defense; if it holds a real claim, state the claim. Keep an objection the text attributes or answers in full, and keep an option a reader would actually weigh.",
        before="This isn't mainly about prompt length, and I'm not arguing that documentation doesn't matter.",
        after="The issue is whether the agent can use the instruction when it acts.",
    ),

    # ── B. Rhythm by rule ─────────────────────────────────────────────────────
    Pattern(
        number=6,
        name="Forced triads",
        category="rhythm_by_rule",
        description="Ideas arrive in threes to sound complete, whether the meaning has three parts or not.",
        watch_for="three parallel examples; three short facts followed by a lesson; 'innovation, inspiration, and insights'.",
        problem="Check that each item adds a distinct idea. Merge examples, develop the strongest one, or vary the structure when they do not.",
        before="The event features keynote sessions, panel discussions, and networking opportunities.",
        after="The event includes talks and panels. There's also time for informal networking between sessions.",
    ),
    Pattern(
        number=7,
        name="Repeated sentence openings",
        category="rhythm_by_rule",
        description="Several sentences in a row start with the same subject.",
        watch_for="several sentences in a row starting with the same subject, often 'she' or 'he'.",
        problem="Merge the sentences, change the subject, or begin with the action. Do not ban the repeated word; a remaining sentence may still start with 'She.'",
        before="She noted the door. She noted the lock on it. She filed both away.",
        after="She noted the door and its lock, then filed both away.",
    ),
    Pattern(
        number=8,
        name="Dashes as the universal connector",
        category="rhythm_by_rule",
        description="A dash lets the writer skip choosing how two clauses relate, so a model reaches for it everywhere.",
        watch_for="em dashes (—) or en dashes (–) used as connectors; spaced dashes; double hyphens (' -- ') used as dashes.",
        problem="Replace each dash with a period, comma, colon, or parentheses, or rewrite the sentence. Leave dashes inside code blocks, inline code, commands, paths, and URLs alone.",
        before="The new policy — announced without warning — affects thousands of workers.",
        after="The new policy, announced without warning, affects thousands of workers.",
        weak_alone=True,
    ),
    Pattern(
        number=9,
        name="Stacked qualifiers",
        category="rhythm_by_rule",
        description="Repeated editing adds one qualifier after another until every claim sounds uncertain.",
        watch_for="to be fair, it's also possible, could potentially, might arguably, in some cases it may, this is an inference.",
        problem="Keep a qualifier only when the source supports it and the meaning needs it. Ordinary hedges such as 'perhaps' or 'tends to' are human habits and not tells.",
        before="It could potentially possibly be argued that the policy might have some effect on outcomes.",
        after="The policy may affect outcomes.",
        weak_alone=True,
    ),
    Pattern(
        number=10,
        name="Hyphenated pairs everywhere",
        category="rhythm_by_rule",
        description="Hyphenated pairs appear in every position.",
        watch_for="third-party, cross-functional, client-facing, data-driven, decision-making, well-known, high-quality, real-time, long-term, end-to-end.",
        problem="Keep the hyphen before a noun when grammar needs it, and drop it after the noun.",
        before="The team is cross-functional, the report is high-quality, and the methodology is data-driven.",
        after="The team is cross functional, the report is high quality, and the methodology is data driven.",
        weak_alone=True,
    ),
    Pattern(
        number=11,
        name="Passive voice and missing subjects",
        category="rhythm_by_rule",
        description="The text hides who acts or drops the subject.",
        watch_for="sentences where the actor is hidden or the subject is missing.",
        problem="Use active voice when it makes the actor and action clearer.",
        before="No configuration file needed. The results are preserved automatically.",
        after="You do not need a configuration file. The system preserves the results automatically.",
        weak_alone=True,
    ),

    # ── C. Inflation and borrowed authority ────────────────────────────────────
    Pattern(
        number=12,
        name="Overused AI words",
        category="inflation",
        description="Models use these words far more often than people do, especially in groups.",
        watch_for="Actually, additionally, align with, bolstered, crucial, deep dive, delve, emphasizing, enduring, enhance, fostering, garner, gate/gated/gating (figurative), highlight (verb), interplay, intricate/intricacies, key (adjective), landscape (abstract noun), meticulous/meticulously, pivotal, quietly, robust (figurative), showcase, tapestry (abstract noun), testament, underscore (verb), valuable, vibrant.",
        problem="Use plain words. A formal word outside this list is not a tell by itself.",
        before="Additionally, a distinctive feature of Somali cuisine is the incorporation of camel meat. An enduring testament to Italian colonial influence is the widespread adoption of pasta in the local culinary landscape.",
        after="Somali cuisine also includes camel meat, which is considered a delicacy. Pasta dishes, introduced during Italian colonization, remain common, especially in the south.",
    ),
    Pattern(
        number=13,
        name="Inflated significance",
        category="inflation",
        description="An ordinary detail is said to mark a change, prove a legacy, or promise a future.",
        watch_for="stands as a testament, a pivotal or crucial moment, plays a key role, marking or shaping the, underscores its importance, reflects a broader, enduring or lasting legacy, setting the stage for, evolving landscape, indelible mark; Despite these challenges... continues to thrive, Challenges and Legacy, Future Outlook, Awards and recognition; the future looks bright, exciting times ahead, a step in the right direction.",
        problem="Keep the fact and drop the significance. End on the last concrete fact; if the source states real plans, use those.",
        before="The Statistical Institute of Catalonia was officially established in 1989, marking a pivotal moment in the evolution of regional statistics in Spain.",
        after="The Statistical Institute of Catalonia was established in 1989, part of a wider decentralization of administrative functions in Spain.",
    ),
    Pattern(
        number=14,
        name="Vague connection or association",
        category="inflation",
        description="The text says two things are connected without saying how.",
        watch_for="associated with, in association with, connected to, in connection with, linked to, tied to.",
        problem="Name the relationship the source gives. If the source does not say, keep the vague wording rather than inventing a role.",
        before="He is associated with the Rajhans Orchestra, which he founded and conducts.",
        after="He founded and conducts the Rajhans Orchestra.",
    ),
    Pattern(
        number=15,
        name="Shallow -ing riders",
        category="inflation",
        description="An -ing phrase is bolted onto a simple fact to make it sound deeper.",
        watch_for="highlighting, underscoring, emphasizing, ensuring, reflecting, symbolizing, contributing to, cultivating, fostering, encompassing, showcasing.",
        problem="Keep the fact; keep the rider only when the source supports what it claims.",
        before="The temple's color palette resonates with the region's natural beauty, symbolizing Texas bluebonnets, the Gulf of Mexico, and the diverse Texan landscapes.",
        after="The temple is painted blue, green, and gold, colors meant to evoke Texas bluebonnets and the Gulf of Mexico.",
    ),
    Pattern(
        number=16,
        name="Sales language",
        category="inflation",
        description="The text reads like an advertisement.",
        watch_for="boasts, vibrant, rich (figurative), profound, enhancing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative), renowned, featuring, diverse array, breathtaking, must-visit, stunning.",
        problem="State what the thing is.",
        before="Nestled within the breathtaking region of Gonder in Ethiopia, Alamata Raya Kobo stands as a vibrant town with a rich cultural heritage and stunning natural beauty.",
        after="Alamata Raya Kobo is a town in the Gonder region of Ethiopia.",
    ),
    Pattern(
        number=17,
        name="Borrowed authority",
        category="inflation",
        description="A name or an unnamed authority stands in for what was said.",
        watch_for="experts argue, observers have cited, industry reports, some critics, several publications; cited, featured, or profiled in [a list of outlets], trade publications, independent coverage; active social media presence, over N followers.",
        problem="When the source text names the real source and what it said, use that. Otherwise cut the unsupported claim or the list. Never invent a source.",
        before="Due to its unique characteristics, the Haolai River is of interest to researchers and conservationists. Experts believe it plays a crucial role in the regional ecosystem.",
        after="Researchers and conservationists study the Haolai River for its unusual characteristics.",
    ),
    Pattern(
        number=18,
        name="Avoiding is, are, and has",
        category="inflation",
        description="Simple verbs are replaced with longer phrases.",
        watch_for="serves as, stands as, functions as, operates as, marks, represents [a]; boasts, features, offers, maintains [a]; refers to.",
        problem="Use 'is', 'are', and 'has'.",
        before="Gallery 825 serves as LAAA's exhibition space for contemporary art. The gallery features four separate spaces and boasts over 3,000 square feet.",
        after="Gallery 825 is LAAA's exhibition space for contemporary art. The gallery has four rooms totaling 3,000 square feet.",
    ),

    # ── D. Formatting by rule ─────────────────────────────────────────────────
    Pattern(
        number=19,
        name="Bold as decoration",
        category="formatting",
        description="Words are bolded without a reason, and vertical lists give every item a bold label and a colon.",
        watch_for="bold text without a reason; labeled lists where every item has a bold label and colon.",
        problem="Remove the bold. Turn a labeled list into prose when the labels carry no information of their own.",
        before="It blends **OKRs (Objectives and Key Results)**, **KPIs (Key Performance Indicators)**, and visual strategy tools.",
        after="It blends OKRs, KPIs, and visual strategy tools like the Business Model Canvas and Balanced Scorecard.",
    ),
    Pattern(
        number=20,
        name="Decorative headings",
        category="formatting",
        description="Headings capitalize every main word, and headings or list items carry emojis or arrows as decoration.",
        watch_for="title case headings; emojis or arrows (→) in headings; horizontal rules between every section; a top-level heading that repeats its own title.",
        problem="Use sentence case, remove the decoration and the rules, and let the title stand once.",
        before="## Strategic Negotiations And Global Partnerships",
        after="## Strategic negotiations and global partnerships",
    ),
    Pattern(
        number=21,
        name="Curly quotation marks",
        category="formatting",
        description="Curly quotes appear where the writer or target format uses straight quotes.",
        watch_for="curly quotes ('...') where straight quotes ('...') are expected.",
        problem="Replace curly quotes with straight quotes.",
        before='He said "the project is on track" but others disagreed.',
        after='He said "the project is on track" but others disagreed.',
        weak_alone=True,
    ),

    # ── E. Leftovers from the chat and the draft ──────────────────────────────
    Pattern(
        number=22,
        name="Chatbot residue",
        category="leftovers",
        description="A chatbot's greeting, praise, offer, or closing remains in text that should stand on its own.",
        watch_for="I hope this helps, Of course!, Certainly!, Great question!, You're absolutely right, Would you like..., Want me to...?, Should I continue?, let me know, here is a...",
        problem="Remove the wrapper and keep the content. This is the most certain tell in this list.",
        before="Great question! Here is an overview of the French Revolution. It began in 1789 when a financial crisis and food shortages led to widespread unrest. I hope this helps!",
        after="The French Revolution began in 1789 when a financial crisis and food shortages led to widespread unrest.",
    ),
    Pattern(
        number=23,
        name="Knowledge-limit disclaimers and guesses",
        category="leftovers",
        description="The text mentions where the model's knowledge ends, or admits it found no source and then fills the gap with a plausible guess.",
        watch_for="as of [date], up to my last training update, while specific details are limited, based on available information, not publicly available, not widely documented or disclosed, in the provided or available sources, maintains a low profile, keeps personal details private, likely [grew up, studied, began], it is believed that.",
        problem="State what the source does not show, or remove the sentence. Never present a guess as a fact.",
        before="While specific details about the company's founding are not extensively documented in readily available sources, it appears to have been established sometime in the 1990s.",
        after="The company's founding date is not documented in the available sources.",
    ),
    Pattern(
        number=24,
        name="A heading repeated in the first sentence",
        category="leftovers",
        description="A heading is followed by a one-line paragraph that restates it before the real content begins.",
        watch_for="a heading followed by a one-sentence paragraph that restates it.",
        problem="Remove the repeated sentence.",
        before="## Performance\n\nSpeed matters.\n\nWhen users hit a slow page, they leave.",
        after="## Performance\n\nWhen users hit a slow page, they leave.",
    ),
    Pattern(
        number=25,
        name="Writing about the document instead of its subject",
        category="leftovers",
        description="Documentation and comments describe what the text replaced instead of the current behavior.",
        watch_for="phrases like 'This function was added to replace...', 'compiled from...', 'The table below compares...'.",
        problem="Describe the subject; state a convention only when the reader cannot see it.",
        before="This function was added to replace the previous approach of iterating through all items, which caused O(n\u00b2) performance.",
        after="This function uses a hash map for O(1) lookups, avoiding the O(n\u00b2) cost of naive iteration.",
    ),

    # ── F. Writing for the wrong reader ───────────────────────────────────────
    Pattern(
        number=26,
        name="Re-explaining what the reader knows",
        category="wrong_reader",
        description="A reply that walks the diagnosis and proves the plan works before the decision.",
        watch_for="a reply that re-explains what the reader already knows before getting to the point.",
        problem="Lead with the decision; leave the diagnosis and the proof for the ticket that follows.",
    ),
]


def get_patterns_as_text() -> str:
    """Formats all patterns as a numbered reference for the system prompt."""
    lines = []
    for p in PATTERNS:
        weak = " (weak alone)" if p.weak_alone else ""
        lines.append(f"{p.number}. **{p.name}**{weak} — {p.description}")
        lines.append(f"   Watch for: {p.watch_for}")
        lines.append(f"   Problem: {p.problem}")
    return "\n".join(lines)


def get_categories() -> dict[str, list[Pattern]]:
    """Groups patterns by category."""
    cats: dict[str, list[Pattern]] = {}
    for p in PATTERNS:
        cats.setdefault(p.category, []).append(p)
    return cats
