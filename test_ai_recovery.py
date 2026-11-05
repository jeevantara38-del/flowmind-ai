import flowmind as fm

@fm.task(name="Fetch Exchange Rates")
def fetch_rates():
    return {"USD": 1.0, "EUR": 0.92}

@fm.task(name="Compute Multiplier")
def compute_multiplier(fetch_rates):
    # This intentionally causes a division by zero error:
    count = 0
    return 100 / count

wf = fm.Workflow("Faulty Pipeline")
t1 = wf.add_task(fetch_rates)
t2 = wf.add_task(compute_multiplier, dependencies=[t1])

result = wf.run()

if result.is_failed:
    print("\n?? A task failed! Calling FlowMind AI Advisor...\n")
    advisor = fm.AIAdvisor()
    failed_task = result.failed_tasks()[0]
    
    # 1. Get plain English diagnosis
    diagnosis = advisor.explain_failure(failed_task)
    print("Diagnosis:   ", diagnosis.summary)
    print("Possible Causes:")
    for cause in diagnosis.possible_causes:
        print(f"  - {cause}")
    print("Action to Fix: ", diagnosis.recommended_action)
