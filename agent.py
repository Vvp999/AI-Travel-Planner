import json
from datetime import datetime
from dotenv import load_dotenv
import anthropic

from weather import get_weather
from route import find_direct_trains
from budget import estimate_trip_cost, fits_budget

load_dotenv()
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from .env
MODEL = "claude-haiku-5-5"

# ---------- Tool descriptions the model sees ----------
TOOLS = [
    {
        "name": "get_weather",
        "description": "Daily weather forecast for a German city: min/max °C and rain chance in %.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'München'"},
                "days": {"type": "integer", "description": "Number of days, 1-7", "default": 3},
            },
            "required": ["city"],
        },
    },
    {
        "name": "find_direct_trains",
        "description": ("Direct long-distance trains between two German stations departing in the "
                        "next few hours. Use full station names like 'Berlin Hbf' or 'Hamburg Hbf'. "
                        "Returns departure, arrival, train and duration in minutes."),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "destination": {"type": "string"},
                "hours": {"type": "integer", "description": "How many hours ahead to search, 1-4", "default": 3},
            },
            "required": ["origin", "destination"],
        },
    },
    {
        "name": "estimate_trip_cost",
        "description": ("Estimate the total trip cost in EUR (round-trip trains, accommodation, food, "
                        "local transport) and check it against the budget. Prices are estimates."),
        "input_schema": {
            "type": "object",
            "properties": {
                "train_type": {"type": "string", "description": "e.g. 'ICE', 'IC', 'RE'"},
                "duration_min": {"type": "integer", "description": "One-way train duration in minutes"},
                "nights": {"type": "integer"},
                "people": {"type": "integer", "default": 1},
                "accommodation": {"type": "string", "enum": ["hostel", "hotel"], "default": "hostel"},
                "budget": {"type": "number", "description": "User's total budget in EUR"},
            },
            "required": ["train_type", "duration_min", "nights", "budget"],
        },
    },
]


# ---------- Run a tool when the model asks for it ----------
def run_tool(name, args):
    try:
        if name == "get_weather":
            return get_weather(args["city"], args.get("days", 3))
        if name == "find_direct_trains":
            trains = find_direct_trains(args["origin"], args["destination"], hours=args.get("hours", 3))
            return [{
                "train": t["train"],
                "departure": t["departure"].strftime("%Y-%m-%d %H:%M"),
                "arrival": t["arrival"].strftime("%Y-%m-%d %H:%M") if t["arrival"] else None,
                "overnight": bool(t["arrival"] and t["arrival"].date() > t["departure"].date()),
                "platform": t["platform"],
                "duration_min": t["duration_min"],
            } for t in trains]
        if name == "estimate_trip_cost":
            est = estimate_trip_cost(
                args["train_type"], args["duration_min"], args["nights"],
                args.get("people", 1), args.get("accommodation", "hostel"),
            )
            est["fits_budget"] = fits_budget(est, args["budget"])
            return est
        return {"error": f"Unknown tool {name}"}
    except Exception as e:
        return {"error": str(e)}


SYSTEM = f"""You are a travel planner for train trips within Germany.
Today is {datetime.now():%A, %d %B %Y, %H:%M}.

Rules:
- Reply in the same language as the user's message; default to English.
- Only use trains, times and prices that come from your tools. Never invent them.
- If the start station, budget or number of nights is missing, ask for it briefly.
- Compare at most 3 candidate destinations to keep tool calls low.
- Check weather and trains for each candidate, then estimate the cost.
- Prices are estimates; say so in the plan.
- If nothing fits the budget, say so honestly and suggest the closest option.

Final answer format:
1. Chosen destination and why (weather, travel time, cost)
2. Outbound train (train, departure, arrival, platform)
3. Day-by-day plan
4. Budget breakdown with total and whether it fits"""


# ---------- Agent loop ----------
def run_agent(messages, verbose=True):
    """Run the agent until it gives a final text answer. Updates messages in place."""
    while True:
        response = client.messages.create(
            model=MODEL, max_tokens=2000, system=SYSTEM, tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        results = []
        for block in response.content:
            if block.type == "tool_use":
                if verbose:
                    print(f"  → {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                output = run_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output, ensure_ascii=False, default=str),
                })
        messages.append({"role": "user", "content": results})


# ---------- Chat in the terminal ----------
if __name__ == "__main__":
    print("Travel planner (type 'quit' to exit)\n")
    messages = []
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        print("\nAgent steps:")
        answer = run_agent(messages)
        print(f"\nPlanner: {answer}\n")
