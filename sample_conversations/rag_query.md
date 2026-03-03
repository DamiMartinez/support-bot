# Sample Conversation: RAG Knowledge Base Query

This transcript demonstrates the agent searching the knowledge base to answer policy questions mid-conversation.

---

**Agent:** Hello! I'm your customer support assistant. How can I help you today?

**Customer:** Hi, before I start — what's your return policy? My package arrived late and I want to know if I can still return it.

> *Agent calls: `search_knowledge_base("return policy late delivery window")`*
> *Knowledge base returns chunks from `returns_policy.md` and `shipping_info.md`*
> *Top result: "Return Window — 30 days from delivery date"*

**Agent:** Great question! Our return policy allows returns within **30 days of delivery**. Since your package only recently arrived (late), you're well within that window. You're eligible for a return or exchange.

For late deliveries specifically, we also want to look into what happened with shipping. Can I get your name and email so we can pull up your order?

**Customer:** Sure. I'm David Chen, david.chen@company.org

> *Agent calls: `save_field("customer_name", "David Chen")`*
> *Agent calls: `validate_email("david.chen@company.org")` → valid*
> *Agent calls: `save_field("email", "david.chen@company.org")`*

**Agent:** Thank you, David. What's your order number?

**Customer:** It's SHIP99001

> *Agent calls: `validate_order_number("SHIP99001")` → valid*
> *Agent calls: `save_field("order_number", "SHIP99001")`*

**Agent:** Got it. What would you say the problem category is — it sounds like a late delivery?

**Customer:** Yes, exactly. It was supposed to arrive 10 days ago but just showed up. How long does standard shipping usually take?

> *Agent calls: `search_knowledge_base("standard shipping delivery time")`*
> *Knowledge base returns from `shipping_info.md`:*
> *"Standard Shipping: 5–7 business days"*

**Agent:** Standard shipping takes **5–7 business days** from the ship date. If your order took significantly longer than that, it qualifies as a late delivery. I'll categorize this accordingly.

Can you describe what happened with your delivery? Any details about tracking or communications you received?

**Customer:** The tracking just said "in transit" for 2 weeks with no updates. Very frustrating. I need it for an event that already passed.

> *Agent calls: `analyze_sentiment("Very frustrating. I need it for an event that already passed.")` → `{"score": 2, "frustrated": true}`*
> *Agent calls: `save_field("problem_category", "late_delivery")`*
> *Agent calls: `save_field("problem_description", "Package showed 'in transit' for 2 weeks with no updates. Arrived 10 days late, missing the event it was needed for.")`*

**Agent:** I'm really sorry the package didn't arrive in time for your event — that's genuinely disappointing, and I understand your frustration.

How would you rate the urgency now that the item has arrived? Would you like to pursue a return/refund, or just flag the shipping issue?

**Customer:** What are my options if I want a refund? Can I get one even though it arrived?

> *Agent calls: `search_knowledge_base("refund late delivery arrived compensation")`*
> *Knowledge base returns from `returns_policy.md`:*
> *"Refund Processing: 5–7 business days... Damaged or defective items: any timeframe"*
> *And from `shipping_info.md`:*
> *"Late Deliveries: contact support with order number"*

**Agent:** Absolutely. Since the item arrived significantly late (missing your event), you have a few options:

1. **Full return & refund** — Send the item back within our 30-day window for a full refund (5–7 business days to your original payment method).
2. **Partial refund / store credit** — Keep the item and we'll compensate for the inconvenience.
3. **Exchange** — Swap for a different item.

Which option would you prefer?

**Customer:** I'll go with option 1, full refund. Urgency is low since the event is over.

> *Agent calls: `save_field("urgency_level", "low")`*

**Agent:** Understood. Here's your ticket summary:

- **Customer:** David Chen
- **Email:** david.chen@company.org
- **Order #:** SHIP99001
- **Category:** Late Delivery
- **Description:** Package showed "in transit" for 2 weeks with no updates. Arrived 10 days late, missing the event it was needed for. Customer requesting full refund.
- **Urgency:** Low

Does this look correct?

**Customer:** Yes, perfect.

> *Agent calls: `finalize_ticket()`*

**Agent:** Your ticket has been created! Confirmation number: **SE-20260227-DC78**. You'll receive a prepaid return label by email within 24 hours. Once we receive the item, your refund will be processed within 5–7 business days to your original payment method. Is there anything else I can help with?

---

## What This Demonstrates

1. **Proactive RAG** — Agent searches the KB before even collecting customer details
2. **Mid-conversation RAG** — Policy questions answered inline without breaking the flow
3. **Multiple KB sources** — `returns_policy.md` + `shipping_info.md` both queried
4. **Sentiment adaptation** — Frustration detected; tone softens
5. **Customer-driven branching** — Return vs. refund vs. exchange explored naturally

## Tools Called (in order)
1. `search_knowledge_base("return policy late delivery window")`
2. `save_field` × 2 (name, email)
3. `validate_email`
4. `validate_order_number`
5. `save_field("order_number", ...)`
6. `search_knowledge_base("standard shipping delivery time")`
7. `analyze_sentiment`
8. `save_field("problem_category", "late_delivery")`
9. `save_field("problem_description", ...)`
10. `search_knowledge_base("refund late delivery arrived compensation")`
11. `save_field("urgency_level", "low")`
12. `finalize_ticket`
