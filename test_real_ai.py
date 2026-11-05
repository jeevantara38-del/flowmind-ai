import os
import flowmind as fm

# 1. Connect the OpenAI adapter (or leave key empty to test the offline fallback)
# Set your key via: $env:OPENAI_API_KEY="sk-..."
api_key = os.getenv("OPENAI_API_KEY")
adapter = fm.OpenAIAdapter(api_key=api_key, model="gpt-4o-mini")
advisor = fm.AIAdvisor(provider=adapter)

# 2. Simulate a broken task
failed_task = fm.TaskResult(
    task_id="fetch_user_records",
    task_name="Fetch User Records",
    status=fm.TaskStatus.FAILED,
    error="KeyError: 'user_id' not found in incoming JSON payload",
    error_type="KeyError",
    is_idempotent=True
)

# 3. Ask the AI for a structured diagnosis and recovery plan
diagnosis = advisor.explain_failure(failed_task)
recovery = advisor.recommend_recovery(failed_task)

print("=" * 60)
print(" FLOWMIND AI ADVISORY DIAGNOSIS")
print("=" * 60)
print(f"Summary:     {diagnosis.summary}")
print(f"Confidence:  {diagnosis.confidence_score * 100:.0f}%")
print("Causes:")
for cause in diagnosis.possible_causes:
    print(f" - {cause}")
print(f"\nRecommended Action: {diagnosis.recommended_action}")
print(f"Safe Fix Plan:      {recovery.suggested_fix}")
print("=" * 60)
