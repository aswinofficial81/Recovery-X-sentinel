from ml.models.recovery_executor import verify_recovery


TRANSACTION_ID = "0abfd9eb-19f7-40ff-9267-82ee3e11ca62"

print()
print("========================================")
print("       TEST RECOVERY VERIFICATION")
print("========================================")

result = verify_recovery(TRANSACTION_ID)

print()
print("========================================")
print("       VERIFICATION RESULT")
print("========================================")

print("Success:")
print(result["success"])

print()
print("Status:")
print(result["status"])

print()
print("Recovered Amount:")
print(
    f"₹{result.get('recovered_amount', 0):,.2f}"
)

print()
print("Message:")
print(result["message"])