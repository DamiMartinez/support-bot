# Sample Conversation: Frustrated Customer (Damaged Item)

This transcript demonstrates sentiment detection and tone adaptation. The agent detects frustration early and switches to a more empathetic mode.

---

**Customer:** This is absolutely ridiculous! My package arrived completely smashed and the item inside is broken. This is unacceptable!

> *Agent calls: `analyze_sentiment("This is absolutely ridiculous! My package arrived completely smashed and the item inside is broken. This is unacceptable!")` → `{"score": 1, "frustrated": true}`*
> *State: `frustration_detected = true`, `sentiment_score = 1`*
> *System prompt now includes the EMPATHY ADDENDUM*
> *Agent calls: `save_field("problem_category", "damaged_item")` (inferred from message)*

**Agent:** I'm truly sorry to hear about your experience — receiving a damaged item is incredibly frustrating, and you absolutely shouldn't have to deal with that. I sincerely apologize for the inconvenience.

I'd like to get this sorted out for you right away. Could I start by getting your name and email address?

**Customer:** Fine. Maria Garcia, maria.garcia@hotmail.com

> *Agent calls: `save_field("customer_name", "Maria Garcia")`*
> *Agent calls: `validate_email("maria.garcia@hotmail.com")` → `{"valid": true}`*
> *Agent calls: `save_field("email", "maria.garcia@hotmail.com")`*

**Agent:** Thank you, Maria. I have your name and email. Could you please share your order number?

**Customer:** ORD-INVALID, that's what's on my receipt

> *Agent calls: `validate_order_number("ORD-INVALID")` → `{"valid": false, "message": "Invalid..."}`*

**Agent:** I'm sorry, I wasn't able to find that order number in our system. Order numbers should be 6-12 alphanumeric characters without dashes. Could you double-check your confirmation email? It might look something like "ORD55512".

**Customer:** Oh wait, it's ORD55512, I misread it. Still furious about this whole situation.

> *Agent calls: `analyze_sentiment("Oh wait, it's ORD55512, I misread it. Still furious about this whole situation.")` → `{"score": 2, "frustrated": true}`*
> *Agent calls: `validate_order_number("ORD55512")` → `{"valid": true}`*
> *Agent calls: `save_field("order_number", "ORD55512")`*

**Agent:** No worries at all — I completely understand your frustration, and I'm sorry this happened. I have your order number ORD55512. Could you describe exactly what was damaged? The more detail you can give, the faster we can process your replacement.

**Customer:** The entire box was crushed. The mug inside was shattered into pieces. There are ceramic shards everywhere. It's a complete mess.

> *Agent calls: `save_field("problem_description", "The entire box was crushed. The mug inside was shattered into pieces with ceramic shards everywhere. Complete damage.")`*

**Agent:** I'm so sorry, Maria. That must have been really alarming to open. No one should receive their order in that condition.

Given the damage, how would you rate the urgency of resolving this? High, medium, or low?

**Customer:** HIGH. Obviously.

> *Agent calls: `save_field("urgency_level", "high")`*

**Agent:** Absolutely, I'll mark this as high priority. Here's a summary:

- **Customer:** Maria Garcia
- **Email:** maria.garcia@hotmail.com
- **Order #:** ORD55512
- **Category:** Damaged Item
- **Description:** The entire box was crushed. The mug inside was shattered into pieces with ceramic shards everywhere.
- **Urgency:** High

Does this look correct?

**Customer:** Yes, just fix it please.

> *Agent calls: `finalize_ticket()`*
> *Ticket created with sentiment_score=2 (frustrated)*

**Agent:** Your ticket has been created — confirmation number **SE-20260227-MG34**. Because this is high urgency, a senior support agent will review it within 2 hours during business hours. We'll send you a prepaid return label and ship a replacement immediately. Again, I'm truly sorry for this experience. Is there anything else I can do for you right now?

---

## What This Demonstrates

1. **Sentiment detection** on first message → `score=1`, `frustrated=true`
2. **Dynamic prompt modification** — empathy addendum added to system prompt
3. **Inline order number correction** — invalid format caught gracefully
4. **Escalation note** — high urgency + frustrated sentiment → senior agent routing
5. **Sentiment score saved** on TicketRecord for analytics

## Tools Called (in order)
1. `analyze_sentiment` (initial message)
2. `save_field("problem_category", "damaged_item")`
3. `save_field` × 2 (name, email)
4. `validate_email`
5. `validate_order_number` (invalid → error)
6. `analyze_sentiment` (second frustrated message)
7. `validate_order_number` (valid)
8. `save_field("order_number", ...)`
9. `save_field("problem_description", ...)`
10. `save_field("urgency_level", "high")`
11. `finalize_ticket`
