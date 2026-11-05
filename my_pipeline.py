import flowmind as fm

@fm.task(retries=3, is_idempotent=True)
def download_data():
    print("Downloading raw records...")
    return [10, 20, 30, 40]

@fm.task
def double_numbers(download_data):
    return [x * 2 for x in download_data]

@fm.task
def save_summary(double_numbers):
    total = sum(double_numbers)
    return f"Processed total: {total}"

workflow = fm.Workflow("My First Pipeline")

step1 = workflow.add_task(download_data)
step2 = workflow.add_task(double_numbers, dependencies=[step1])
step3 = workflow.add_task(save_summary, dependencies=[step2])

result = workflow.run()

print(result.summary())
print("Final Output:", result.get_output(step3.id))
