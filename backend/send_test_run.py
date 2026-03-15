import os

from sdk_flight_recorder import FlightRecorder

if __name__ == "__main__":
    api_key = os.environ.get("FLIGHT_RECORDER_API_KEY") or os.environ.get("API_KEY")
    rec = FlightRecorder(
        api_base_url="http://localhost:8000",
        agent_id="demo-agent",
        agent_version="v0",
        api_key=api_key,
    )

    user_query = "Who was the first person to walk on the moon and in which year?"
    rec.start_run(user_query, env={"model": "gpt-4o-mini"})

    # Fake steps; in a real agent you'd log each thought/tool call
    rec.log_step(
        idx=0,
        step_type="thought",
        request={"thought": "Recall Apollo missions"},
        response=None,
    )

    # Pretend this is the model’s final answer
    final_answer = "The first person was Neil Armstrong in 1969."

    # Send run + steps to backend
    result = rec.end_run(final_answer)
    print("Recorded run:", result)