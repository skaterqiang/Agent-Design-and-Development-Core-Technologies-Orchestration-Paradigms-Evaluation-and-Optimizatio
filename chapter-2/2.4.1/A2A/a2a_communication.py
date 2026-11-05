# a2a_communication.py
import asyncio
import aiohttp
import os
import uuid


async def send_a2a_message(session, port, assistant_id, text):
    """Send A2A message to an agent"""
    url = f"http://127.0.0.1:{port}/a2a/{assistant_id}"
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                # A2A 协议要求 messageId 非空；langgraph-api 0.16.0 会严格校验，
                # 留空会返回 {"error": {"code": -32602, "message": "Missing required 'messageId' in message"}}
                "messageId": str(uuid.uuid4()),
            },
            "messageId": str(uuid.uuid4()),
            "thread": {"threadId": ""}
        }
    }

    async with session.post(url, json=payload, headers={"Accept": "application/json"}) as response:
        result = await response.json()
        return result["result"]["artifacts"][0]["parts"][0]["text"]


async def plan_trip_with_flight():
    """智能体1负责规划行程，然后与智能体2沟通以预订航班。"""
    trip_planner_id = "f435c2be-87ce-5de8-bb36-70054bb12b8b"
    flight_booker_id = "73cda8b2-d794-58ac-9efa-3557bfd39b40"

    async with aiohttp.ClientSession() as session:
        # 步骤1：旅行规划员制定行程
        trip_request = "请帮忙规划一个到巴黎的三天旅程"
        trip_plan = await send_a2a_message(session, 2024, trip_planner_id, trip_request)
        print(f"Trip Planner: {trip_plan}\n")

        # 步骤2：旅行规划员请航班预订员搜索航班
        flight_request = f"根据以下行程计划：{trip_plan}，搜索从纽约（NYC）飞往巴黎、下周一的航班。"
        flight_options = await send_a2a_message(session, 2025, flight_booker_id, flight_request)
        print(f"Flight Booker: {flight_options}\n")

        # 步骤3：旅行规划员确认预订
        booking_request = "为李明预订价格较低的航班。"
        confirmation = await send_a2a_message(session, 2025, flight_booker_id, booking_request)
        print(f"Flight Booker: {confirmation}")


if __name__ == "__main__":
    asyncio.run(plan_trip_with_flight())

