# Sample Conversation: Standard Issue (Wrong Item)

This transcript demonstrates the happy-path flow: all data collected cleanly in sequence, ticket finalized.

---

**Agent:** Hi there! I'm the Orbio customer support assistant. I'm here to help you resolve any issues with your order. Could I start with your full name and email address?

**Customer:** Sure, my name is John Smith and my email is john.smith@example.com

> *Agent internally calls: `save_field("customer_name", "John Smith")`, `validate_email("john.smith@example.com")`, `save_field("email", "john.smith@example.com")`*
> *Phase advances: COLLECT_IDENTITY → COLLECT_ORDER*

**Agent:** Thanks, John! Now, could you please share your order number?

**Customer:** My order number is ORD78901

> *Agent calls: `validate_order_number("ORD78901")` → `{"valid": true}`*
> *Agent calls: `save_field("order_number", "ORD78901")`*
> *Phase advances: COLLECT_ORDER → COLLECT_ISSUE*

**Agent:** Got it. What seems to be the problem with your order?

**Customer:** I received the wrong item. I ordered a blue shirt in size medium but I got a red one instead.

> *Agent calls: `save_field("problem_category", "wrong_item")`*
> *Agent calls: `save_field("problem_description", "I ordered a blue shirt in size medium but received a red one instead.")`*
> *Phase advances: COLLECT_ISSUE → COLLECT_URGENCY*

**Agent:** I understand — receiving the wrong item is frustrating. How urgent is this for you? Please rate it as low, medium, or high.

**Customer:** Medium, I don't need it immediately but I'd like it resolved within the week.

> *Agent calls: `save_field("urgency_level", "medium")`*
> *Phase advances: COLLECT_URGENCY → CONFIRM*

**Agent:** Here's a summary of your support request:

- **Customer:** John Smith
- **Email:** john.smith@example.com
- **Order #:** ORD78901
- **Category:** Wrong Item
- **Description:** I ordered a blue shirt in size medium but received a red one instead.
- **Urgency:** Medium

Does everything look correct? Shall I go ahead and create your support ticket?

**Customer:** Yes, that's all correct, please proceed.

> *Agent calls: `finalize_ticket()`*
> *System writes ticket to `data/tickets/<uuid>.json`*
> *Phase advances: CONFIRM → COMPLETED*
> *Confirmation number generated: SE-20260227-AB12*

**Agent:** Your support ticket has been created successfully! Your confirmation number is **SE-20260227-AB12**. Our team will review your case and reach out within 1-2 business days. We'll ship the correct blue shirt with express delivery. Is there anything else I can help you with?

**Customer:** No, thank you!

**Agent:** You're welcome, John! Have a great day, and we'll be in touch soon to resolve your order.

---

## Data Extracted

```json
{
  "customer_name": "John Smith",
  "email": "john.smith@example.com",
  "order_number": "ORD78901",
  "problem_category": "wrong_item",
  "problem_description": "I ordered a blue shirt in size medium but received a red one instead.",
  "urgency_level": "medium"
}
```

## Tools Called (in order)
1. `save_field` × 2 (name, email)
2. `validate_email`
3. `validate_order_number`
4. `save_field` (order_number)
5. `save_field` × 2 (problem_category, problem_description)
6. `save_field` (urgency_level)
7. `finalize_ticket`
