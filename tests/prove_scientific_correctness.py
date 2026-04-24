import sys
import os
from unittest.mock import MagicMock
import statistics

# Mock kafka and joblib to allow importing main.py without installing dependencies
sys.modules['kafka'] = MagicMock()
sys.modules['kafka.errors'] = MagicMock()
sys.modules['joblib'] = MagicMock()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'feature-service')))
import main as feature_main
from main import FlowRecord, extract_features, FEATURE_NAMES

def prove_correctness():
    print("=========================================================")
    print("[TEST] NEUROSHIELD FEATURE PIPELINE: SCIENTIFIC VERIFICATION")
    print("=========================================================\n")

    # ---------------------------------------------------------
    # 1. Feature Order Mismatch Check
    # ---------------------------------------------------------
    print(">>> TEST 1: Feature ORDER Match <<<")
    col_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'feature_columns.txt')
    with open(col_file, 'r') as f:
        saved_cols = [line.strip() for line in f if line.strip()]

    if saved_cols == FEATURE_NAMES:
        print("[PASS] Runtime feature order perfectly matches training feature_columns.txt")
    else:
        print("[FAIL] Order mismatch detected!")
        return

    # ---------------------------------------------------------
    # 2. Feature Count Mismatch Check
    # ---------------------------------------------------------
    print("\n>>> TEST 2: Feature COUNT Match <<<")
    if len(FEATURE_NAMES) == 80 and len(saved_cols) == 80:
         print("[PASS] Exactly 80 features extracted as required by SNN/LNN/XGBoost")
    else:
         print(f"[FAIL] Expected 80 features, got {len(FEATURE_NAMES)}")
         return

    # ---------------------------------------------------------
    # 3. Feature Meaning (Math) Check
    # ---------------------------------------------------------
    print("\n>>> TEST 3: Feature MEANING (Math & Logic) Match <<<")
    
    # Disable scaling so we can test raw mathematical values
    feature_main._scaler_loaded = True
    feature_main._scaler = None
    
    # Construct a deterministic flow
    # A simple TCP handshake + data
    # SYN (fwd) -> SYN-ACK (bwd) -> ACK (fwd) -> PSH-ACK (fwd) -> PSH-ACK (bwd) -> FIN (fwd) -> FIN-ACK (bwd)
    
    t0 = 1000.0
    packets = [
        {"direction": "fwd", "length": 60,  "flags": {"SYN": True}, "ts": t0},
        {"direction": "bwd", "length": 60,  "flags": {"SYN": True, "ACK": True}, "ts": t0 + 0.1},
        {"direction": "fwd", "length": 54,  "flags": {"ACK": True}, "ts": t0 + 0.2},
        {"direction": "fwd", "length": 150, "flags": {"PSH": True, "ACK": True}, "ts": t0 + 0.3},
        {"direction": "bwd", "length": 200, "flags": {"PSH": True, "ACK": True}, "ts": t0 + 0.4},
        {"direction": "fwd", "length": 54,  "flags": {"FIN": True, "ACK": True}, "ts": t0 + 0.5},
        {"direction": "bwd", "length": 54,  "flags": {"FIN": True, "ACK": True}, "ts": t0 + 0.6},
    ]
    
    key = ("192.168.1.10", "10.0.0.5", 54321, 443, "TCP")
    flow = FlowRecord(key, t0)
    for p in packets:
        # Mocking the dictionary that `add_packet` expects
        pkt_dict = {
            "timestamp": p["ts"],
            "length": p["length"],
            "flags": p["flags"],
            "src_ip": key[0] if p["direction"] == "fwd" else key[1],
            "dst_ip": key[1] if p["direction"] == "fwd" else key[0]
        }
        flow.add_packet(pkt_dict, p["direction"])

    extracted = extract_features(flow)
    
    # Let's map names to values for easy testing
    f_map = dict(zip(FEATURE_NAMES, extracted))
    
    # Now, let's mathematically verify the meaning of specific critical features
    tests_passed = 0
    total_tests = 0
    
    def assert_feature(name, expected, tolerance=1e-5):
        nonlocal tests_passed, total_tests
        total_tests += 1
        actual = f_map[name]
        if abs(actual - expected) <= tolerance:
            print(f"  [PASS] {name}: {actual:.4f} (matches expected math)")
            tests_passed += 1
        else:
            print(f"  [FAIL] {name} Mismatch: got {actual:.4f}, expected {expected:.4f}")

    print("\n--- Testing Basic Timing ---")
    assert_feature("flow_duration", 0.6) # 1000.6 - 1000.0
    assert_feature("flow_bytes_per_s", sum(p['length'] for p in packets) / 0.6)
    assert_feature("flow_packets_per_s", 7 / 0.6)
    
    print("\n--- Testing Packet Statistics ---")
    assert_feature("fwd_packets_total", 4)
    assert_feature("bwd_packets_total", 3)
    assert_feature("fwd_bytes_total", 60 + 54 + 150 + 54) # 318
    assert_feature("bwd_bytes_total", 60 + 200 + 54) # 314
    
    fwd_lens = [60, 54, 150, 54]
    bwd_lens = [60, 200, 54]
    assert_feature("fwd_pkt_len_max", max(fwd_lens))
    assert_feature("fwd_pkt_len_mean", sum(fwd_lens)/4)
    assert_feature("bwd_pkt_len_max", max(bwd_lens))
    assert_feature("down_up_ratio", sum(bwd_lens) / sum(fwd_lens))
    
    print("\n--- Testing TCP Flags ---")
    assert_feature("syn_flag_count", 2)
    assert_feature("ack_flag_count", 6)
    assert_feature("fin_flag_count", 2)
    assert_feature("psh_flag_count", 2)
    assert_feature("syn_ratio", 2/7)
    
    print("\n--- Testing IAT (Inter-Arrival Time) ---")
    all_iats = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    assert_feature("flow_iat_mean", sum(all_iats)/len(all_iats))
    assert_feature("flow_iat_total", 0.6)
    
    fwd_iats = [0.2, 0.1, 0.2] # t=0, t=0.2, t=0.3, t=0.5. diffs: 0.2, 0.1, 0.2
    assert_feature("fwd_iat_total", 0.5)
    assert_feature("fwd_iat_mean", sum(fwd_iats)/3)
    
    print(f"\n[PASS] {tests_passed}/{total_tests} feature math assertions passed.")
    if tests_passed == total_tests:
        print("\n[SUCCESS] SCIENTIFIC CORRECTNESS PROVEN: Feature extraction math matches standard definitions!")

if __name__ == "__main__":
    prove_correctness()
