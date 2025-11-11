from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models.transactions import Payment
from xrpl.utils import xrp_to_drops
from xrpl.transaction import autofill, sign, submit_and_wait
from xrpl.models.requests import AccountInfo
import time

# Connect to official XRPL Devnet
client = JsonRpcClient("https://s.devnet.rippletest.net:51234")

# Attacker account
attacker_seed = "sEdTh4D8djVSnf8ehCztyuZnYx6G4F8"
attacker_wallet = Wallet.from_seed(attacker_seed)

# Lender account
lender_seed = "sEdTLePoKgereP1MiQPQSxsNmjpkW5Y"
lender_wallet = Wallet.from_seed(lender_seed)

print(f"👤 Attacker: {attacker_wallet.classic_address}")
print(f"💰 Lender: {lender_wallet.classic_address}")

# Check account balance
def check_balance(address):
    req = AccountInfo(account=address, ledger_index="validated")
    resp = client.request(req)
    balance = int(resp.result["account_data"]["Balance"]) / 1_000_000
    print(f"🔎 Balance of {address}: {balance} XRP")
    return balance

check_balance(attacker_wallet.classic_address)
check_balance(lender_wallet.classic_address)

# Vulnerable loan contract class
class VulnerableLoanContractXRPL:
    def __init__(self, client, attacker_wallet, lender_wallet):
        self.client = client
        self.attacker = attacker_wallet
        self.lender = lender_wallet
        self.loan_amount = 0
        self.loan_repaid = False

    def request_loan(self, amount_xrp):
        print("\n📤 Requesting loan...")
        self.loan_amount = amount_xrp
        drops = xrp_to_drops(amount_xrp)
        tx = Payment(
            account=self.lender.classic_address,
            destination=self.attacker.classic_address,
            amount=drops
        )
        tx = autofill(tx, self.client)
        signed = sign(tx, self.lender)
        resp = submit_and_wait(signed, self.client)
        result = resp.result["meta"]["TransactionResult"]
        print("Loan TX:", result)
        print("Loan Hash:", resp.result["hash"])
        if result == "tesSUCCESS":
            print("✅ Done")
        else:
            print("❌ Transaction failed")

    def repay_loan(self, repay_amount_xrp):
        print("\n💸 Repaying loan (partial)...")
        drops = xrp_to_drops(repay_amount_xrp)
        tx = Payment(
            account=self.attacker.classic_address,
            destination=self.lender.classic_address,
            amount=drops
        )
        tx = autofill(tx, self.client)
        signed = sign(tx, self.attacker)
        resp = submit_and_wait(signed, self.client)
        result = resp.result["meta"]["TransactionResult"]
        print("Repay TX:", result)
        print("Repay Hash:", resp.result["hash"])
        if result == "tesSUCCESS":
            self.loan_repaid = True
            print("✅ Done")
        else:
            print("❌ Transaction failed")
        return result

    def withdraw_funds(self, amount_xrp):
        print("\n🏧 Attempting withdrawal from lender...")
        if not self.loan_repaid:
            print("❌ Withdrawal denied: Loan not repaid.")
            return
        drops = xrp_to_drops(amount_xrp)
        tx = Payment(
            account=self.lender.classic_address,
            destination=self.attacker.classic_address,
            amount=drops
        )
        tx = autofill(tx, self.client)
        signed = sign(tx, self.lender)
        resp = submit_and_wait(signed, self.client)
        result = resp.result["meta"]["TransactionResult"]
        print("Withdraw TX:", result)
        print("Withdraw Hash:", resp.result["hash"])
        if result == "tesSUCCESS":
            print("✅ Done")
        else:
            print("❌ Transaction failed")

# Run test scenario with <2 XRP
contract = VulnerableLoanContractXRPL(client, attacker_wallet, lender_wallet)

# Step 1: Request loan of 1.5 XRP
contract.request_loan(1.5)
time.sleep(4)
check_balance(attacker_wallet.classic_address)
check_balance(lender_wallet.classic_address)

# Step 2: Repay only 0.5 XRP
contract.repay_loan(0.5)
time.sleep(4)
check_balance(attacker_wallet.classic_address)
check_balance(lender_wallet.classic_address)

# Step 3: Attempt to withdraw full loan amount (1.5 XRP)
contract.withdraw_funds(1.5)
time.sleep(4)
check_balance(attacker_wallet.classic_address)
check_balance(lender_wallet.classic_address)

print("\n🚨 If withdrawal succeeds despite partial repayment, the vulnerability is confirmed.")