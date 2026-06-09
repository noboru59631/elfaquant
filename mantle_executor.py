"""
Mantle上でFluxion経由のMNT→USDTスワップを実行する。
フロー: wrap_mnt → approve_token → execute_swap
"""
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError

load_dotenv(Path(__file__).resolve().parent / ".env")

_pk = os.getenv("MANTLE_PRIVATE_KEY", "")
PRIVATE_KEY    = _pk if _pk.startswith("0x") else "0x" + _pk
WALLET_ADDRESS = os.getenv("MANTLE_WALLET_ADDRESS")
RPC_URL        = os.getenv("MANTLE_RPC", "https://rpc.mantle.xyz")

# Mantle mainnet addresses (source: Fluxion-trade-skill/references/contracts.md)
WMNT_ADDRESS   = Web3.to_checksum_address("0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8")  # decimals: 18
USDT_ADDRESS   = Web3.to_checksum_address("0x779Ded0c9e1022225f8E0630b35a9b54bE713736")  # decimals: 6
ROUTER_ADDRESS  = Web3.to_checksum_address("0x5628a59dF0ECAC3f3171f877A94bEb26BA6DFAa0")
FACTORY_ADDRESS = Web3.to_checksum_address("0xF883162Ed9c7E8EF604214c964c678E40c9B737C")
QUOTER_ADDRESS  = Web3.to_checksum_address("0x3E4eE18Ac7280813236a1EB850679Da5322E14CE")
QUOTE_URL       = "https://skillapi.fluxion.network/quote/exact-in"
CHAIN_ID        = 5000

FACTORY_ABI = [{
    "name": "getPool", "type": "function", "stateMutability": "view",
    "inputs": [
        {"name": "tokenA", "type": "address"},
        {"name": "tokenB", "type": "address"},
        {"name": "fee",    "type": "uint24"},
    ],
    "outputs": [{"name": "pool", "type": "address"}],
}]

POOL_ABI = [
    {"name": "liquidity", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint128"}]},
    {"name": "slot0", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [
         {"name": "sqrtPriceX96", "type": "uint160"},
         {"name": "tick", "type": "int24"},
         {"name": "observationIndex", "type": "uint16"},
         {"name": "observationCardinality", "type": "uint16"},
         {"name": "observationCardinalityNext", "type": "uint16"},
         {"name": "feeProtocol", "type": "uint8"},
         {"name": "unlocked", "type": "bool"},
     ]},
]

WMNT_ABI = [
    {"name": "deposit",   "type": "function", "stateMutability": "payable",
     "inputs": [], "outputs": []},
    {"name": "approve",   "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "guy", "type": "address"}, {"name": "wad", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"name": "allowance", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "transferFrom", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "src", "type": "address"}, {"name": "dst", "type": "address"}, {"name": "wad", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
]

QUOTER_ABI = [{
    "name": "quoteExactInputSingle", "type": "function", "stateMutability": "nonpayable",
    "inputs": [{"name": "params", "type": "tuple", "components": [
        {"name": "tokenIn",          "type": "address"},
        {"name": "tokenOut",         "type": "address"},
        {"name": "amountIn",         "type": "uint256"},
        {"name": "fee",              "type": "uint24"},
        {"name": "sqrtPriceLimitX96","type": "uint160"},
    ]}],
    "outputs": [
        {"name": "amountOut",                "type": "uint256"},
        {"name": "sqrtPriceX96After",        "type": "uint160"},
        {"name": "initializedTicksCrossed",   "type": "uint32"},
        {"name": "gasEstimate",              "type": "uint256"},
    ],
}]

w3       = Web3(Web3.HTTPProvider(RPC_URL))
account  = w3.eth.account.from_key(PRIVATE_KEY)
wmnt     = w3.eth.contract(address=WMNT_ADDRESS, abi=WMNT_ABI)
factory  = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)
quoter   = w3.eth.contract(address=QUOTER_ADDRESS, abi=QUOTER_ABI)


def check_pool(fee: int) -> str:
    """指定fee tierのプールアドレスを返す。存在しなければzero addressを返す。"""
    pool_addr = factory.functions.getPool(WMNT_ADDRESS, USDT_ADDRESS, fee).call()
    return pool_addr


def _send_tx(tx: dict) -> str:
    """Sign, broadcast, wait for receipt. Returns tx hash string."""
    signed   = account.sign_transaction(tx)
    tx_hash  = w3.eth.send_raw_transaction(signed.raw_transaction)
    hash_hex = tx_hash.hex()
    print(f"  送信完了: {hash_hex}")
    print("  receipt待機中...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    status  = "成功" if receipt.status == 1 else "失敗"
    print(f"  [{status}] block={receipt.blockNumber} gas={receipt.gasUsed}")
    if receipt.status != 1:
        raise RuntimeError(f"Transaction reverted: {hash_hex}")
    return hash_hex


def _simulate(tx: dict) -> None:
    """eth_callでリバート理由を取得して表示する。"""
    try:
        w3.eth.call(tx)
        print("  [simulate] OK - リバートなし")
    except ContractLogicError as e:
        print(f"  [simulate] リバート理由: {e}")
    except Exception as e:
        print(f"  [simulate] エラー: {e}")


def wrap_mnt(amount_mnt: float) -> str:
    """ネイティブMNTをWMNTにラップする (WMNT.deposit)."""
    amount_wei = int(amount_mnt * 10**18)
    print(f"\n[WRAP] {amount_mnt} MNT → WMNT ({amount_wei} wei)")
    nonce = w3.eth.get_transaction_count(account.address)
    tx = wmnt.functions.deposit().build_transaction({
        "from":     account.address,
        "value":    amount_wei,
        "nonce":    nonce,
        "gas":      60000,
        "gasPrice": w3.eth.gas_price,
        "chainId":  CHAIN_ID,
    })
    return _send_tx(tx)


def approve_token() -> str:
    """WMNTのRouterへの無制限approveを実行する（未承認の場合のみ）。"""
    max_uint256 = 2**256 - 1
    allowance   = wmnt.functions.allowance(account.address, ROUTER_ADDRESS).call()
    print(f"\n[APPROVE] 現在のallowance: {allowance}")
    if allowance > 10**18:
        print("[APPROVE] 承認済み - スキップ")
        return ""
    print("[APPROVE] WMNT → Router approve (unlimited)")
    nonce = w3.eth.get_transaction_count(account.address)
    tx = wmnt.functions.approve(ROUTER_ADDRESS, max_uint256).build_transaction({
        "from":     account.address,
        "nonce":    nonce,
        "gas":      60000,
        "gasPrice": w3.eth.gas_price,
        "chainId":  CHAIN_ID,
    })
    return _send_tx(tx)


def execute_swap(amount_mnt: float) -> str:
    """Fluxion Quote APIからcalldataを取得してWMNT→USDTスワップを実行する。"""
    amount_wei = int(amount_mnt * 10**18)
    print(f"\n[SWAP] {amount_mnt} WMNT → USDT ({amount_wei} wei)")

    body = {
        "inputMint":       WMNT_ADDRESS,
        "outputMint":      USDT_ADDRESS,
        "amount":          str(amount_wei),
        "userPublicKey":   account.address,
        "dynamicSlippage": False,
        "slippageBps":     "100",
    }
    resp = requests.post(QUOTE_URL, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    out_amount = int(data["outAmount"]) / 10**6
    min_out    = int(data["minOutAmount"]) / 10**6
    print(f"  見積もり: {out_amount:.4f} USDT (最低 {min_out:.4f} USDT, impact={data.get('priceImpact')}%)")

    tx_data  = data["tx"]
    raw_data = tx_data["data"]

    # calldataのdeadline (param 4) をブロックタイムスタンプ+10分に差し替える
    # layout: 0x + 8chars selector + n*64chars params
    block_ts      = w3.eth.get_block("latest")["timestamp"]
    new_deadline  = block_ts + 600  # 10分後
    new_dl_hex    = hex(new_deadline)[2:].zfill(64)
    dl_start      = 2 + 8 + 4 * 64   # "0x"(2) + selector(8) + params 0-3 (4*64)
    raw_data      = raw_data[:dl_start] + new_dl_hex + raw_data[dl_start + 64:]
    print(f"  deadline: 旧={hex(0x6a2837cc)} → 新={hex(new_deadline)} (block_ts={block_ts})")

    # amountOutMinimum (param 6) を 0 に設定してスリッページ保護を無効化（テスト用）
    ao_start = 2 + 8 + 6 * 64
    raw_data = raw_data[:ao_start] + "0" * 64 + raw_data[ao_start + 64:]
    print("  amountOutMinimum: 0 (スリッページ無効化テスト)")

    nonce = w3.eth.get_transaction_count(account.address)
    api_gas = int(tx_data["gasLimit"])
    # QuoterV2のgasEstimateはcallback内のtransferFrom(~40000gas)を含まないため
    # APIのgasLimit(114096)は不足する可能性がある → 余裕を持って300000に固定
    gas_limit = max(api_gas * 3, 300000)
    print(f"  gasLimit: API={api_gas} → 使用={gas_limit}")
    tx = {
        "from":     account.address,
        "to":       Web3.to_checksum_address(tx_data["to"]),
        "data":     raw_data,
        "value":    int(tx_data.get("value", 0)),
        "gas":      gas_limit,
        "gasPrice": int(tx_data["gasPrice"]),
        "nonce":    nonce,
        "chainId":  CHAIN_ID,
    }

    print("  [simulate] eth_callで事前チェック...")
    _simulate({k: v for k, v in tx.items() if k != "nonce"})

    return _send_tx(tx)


if __name__ == "__main__":
    amount = 0.1

    print("=== Mantle Fluxion Swap ===")
    print(f"Wallet    : {account.address}")
    mnt_bal   = w3.from_wei(w3.eth.get_balance(account.address), "ether")
    wmnt_bal  = w3.from_wei(wmnt.functions.balanceOf(account.address).call(), "ether")
    allowance = wmnt.functions.allowance(account.address, ROUTER_ADDRESS).call()
    router_code = w3.eth.get_code(ROUTER_ADDRESS)
    print(f"MNT残高   : {mnt_bal:.4f} MNT")
    print(f"WMNT残高  : {wmnt_bal:.4f} WMNT")
    print(f"Allowance : {allowance}")
    print(f"Routerコード長: {len(router_code)} bytes")

    print("\n[POOL CHECK] WMNT/USDT0 プール確認...")
    ZERO = "0x0000000000000000000000000000000000000000"
    for fee in [500, 3000, 10000]:
        pool_addr = check_pool(fee)
        if pool_addr == ZERO:
            print(f"  fee={fee:>5}: プール未存在")
        else:
            pool = w3.eth.contract(address=pool_addr, abi=POOL_ABI)
            liq = pool.functions.liquidity().call()
            slot0 = pool.functions.slot0().call()
            print(f"  fee={fee:>5}: {pool_addr} | liquidity={liq} | unlocked={slot0[6]}")
    pool_addr = check_pool(3000)
    # ルーターが INIT_CODE_HASH から計算するプールアドレスと実アドレスを比較
    print("\n[INIT_CODE_HASH] ルーターのプールアドレス計算検証...")
    from eth_abi import encode as abi_encode
    UNISWAP_V3_INIT_CODE_HASH = bytes.fromhex("e34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54")
    token0, token1 = sorted([WMNT_ADDRESS.lower(), USDT_ADDRESS.lower()])
    salt = w3.keccak(abi_encode(["address", "address", "uint24"], [
        Web3.to_checksum_address(token0), Web3.to_checksum_address(token1), 3000
    ]))
    computed_pool = Web3.to_checksum_address("0x" + w3.keccak(
        b'\xff'
        + bytes.fromhex(FACTORY_ADDRESS[2:])
        + salt
        + UNISWAP_V3_INIT_CODE_HASH
    ).hex()[-40:])
    print(f"  実際のプール  : {pool_addr}")
    print(f"  ルーター計算値: {computed_pool}")
    print(f"  一致          : {computed_pool.lower() == pool_addr.lower()}")

    print(f"\n[TRANSFER_SIM] WMNT.transferFrom シミュレーション (user→pool)...")
    try:
        tf_result = wmnt.functions.transferFrom(
            account.address, pool_addr, int(amount * 10**18)
        ).call({"from": ROUTER_ADDRESS})
        print(f"  transferFrom結果: {tf_result}")
    except Exception as e:
        print(f"  transferFrom失敗: {e}")

    print("\n[QUOTER2] QuoterV2でスワップシミュレーション...")
    try:
        result = quoter.functions.quoteExactInputSingle({
            "tokenIn":           WMNT_ADDRESS,
            "tokenOut":          USDT_ADDRESS,
            "amountIn":          int(amount * 10**18),
            "fee":               3000,
            "sqrtPriceLimitX96": 0,
        }).call()
        print(f"  amountOut={result[0]} ({result[0]/10**6:.4f} USDT) gasEst={result[3]}")
    except Exception as e:
        print(f"  QuoterV2 失敗: {e}")

    print(f"\n実行量    : {amount} MNT\n")

    # wrap/approve は既に完了済みのためスキップ（WMNT残高あり・approve済み）
    # wrap_mnt(amount)
    # time.sleep(2)
    # approve_token()
    # time.sleep(2)

    tx_hash = execute_swap(amount)

    print(f"\n=== 完了 ===")
    print(f"Tx hash : {tx_hash}")
    print(f"Explorer: https://explorer.mantle.xyz/tx/{tx_hash}")
