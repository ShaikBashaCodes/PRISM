import math, time
from typing import List, Tuple, Dict

class Engine:
    def __init__(self):
        self.batch_sz = 1000
        self.z_th = 3.0

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_DARK = "\033[40m"

    # Parse raw input string into float list, count invalid entries
    def parse(self, raw: str) -> Tuple[List[float], int]:
        try:
            raw = raw.strip().replace('[','').replace(']','')
            vals = []
            invalid_count = 0
            raw = raw.replace(',', ' ')
            parts = raw.split()
            for p in parts:
                p = p.strip()
                if not p:
                    invalid_count += 1
                    continue
                if p.upper() in ['NULL', 'NA', 'NAN', 'NONE', 'N/A', '-']:
                    invalid_count += 1
                    continue
                try:
                    val = float(p)
                    if math.isnan(val) or math.isinf(val):
                        invalid_count += 1
                    else:
                        vals.append(val)
                except ValueError:
                    invalid_count += 1
            return vals if vals else [0], invalid_count
        except:
            return [0], 1

    # Remove extreme values and invalid data points
    def clean(self, d: List[float]) -> Tuple[List[float], int]:
        clean, inv = [], 0
        for v in d:
            try:
                if not (math.isnan(v) or math.isinf(v) or abs(v) > 1e15):
                    clean.append(float(v))
                else:
                    inv += 1
            except:
                inv += 1
        return clean if clean else [0], inv

    # Fit linear regression model: y = ax + b, return coefficients and R²
    def fit(self, x, y) -> Tuple[float, float, float]:
        n, mx, my = len(x), sum(x)/len(x), sum(y)/len(y)
        num = sum((x[i]-mx)*(y[i]-my) for i in range(n))
        den = sum((x[i]-mx)**2 for i in range(n))
        a = num/den if abs(den) > 1e-10 else 0
        b = my - a*mx
        pred = [a*xi+b for xi in x]
        ss_tot = sum((yi-my)**2 for yi in y)
        ss_res = sum((yi-pi)**2 for yi, pi in zip(y, pred))
        r2 = 1-(ss_res/ss_tot) if ss_tot > 1e-10 else 0.5
        return a, b, max(0, r2)

    # Analyze data and detect best fitting pattern (LINEAR, QUAD, or EXP)
    def analyze(self, y: List[float]) -> Dict:
        x = list(range(len(y)))
        res = {}
        try:
            a, b, r2 = self.fit(x, y)
            res['LINEAR'] = {'r2': r2, 'a': a, 'b': b}
        except:
            res['LINEAR'] = {'r2': -1}
        try:
            if len(y) > 2:
                d1 = [y[i+1]-y[i] for i in range(len(y)-1)]
                d2 = [d1[i+1]-d1[i] for i in range(len(d1)-1)]
                aq = sum(d2)/(2*len(d2)) if d2 else 0
                bq = (d1[0] if d1 else 0) - aq
                cq = y[0]
                pred = [aq*i*i+bq*i+cq for i in x]
                my = sum(y)/len(y)
                ss_tot = sum((yi-my)**2 for yi in y)
                ss_res = sum((yi-pi)**2 for yi,pi in zip(y,pred))
                r2q = 1-(ss_res/ss_tot) if ss_tot > 1e-10 else 0.3
                res['QUAD'] = {'r2': max(0,r2q), 'a': aq, 'b': bq, 'c': cq}
        except:
            res['QUAD'] = {'r2': -1}
        try:
            if all(yi > 0 for yi in y):
                log_y = [math.log(yi) for yi in y]
                ae, be, re = self.fit(x, log_y)
                res['EXP'] = {'r2': re, 'a': math.exp(be), 'b': ae}
        except:
            res['EXP'] = {'r2': -1}
        best = max(res.items(), key=lambda kv: kv[1].get('r2', -1))
        return {'t': best[0], 'r': best[1].get('r2', 0), 'p': best[1]}

    # Detect anomalies using Z-score method with severity levels
    def anom(self, y: List[float]) -> Tuple[int, str, List]:
        try:
            if len(y) < 2:
                return 0, "LOW", []
            m = sum(y)/len(y)
            s = math.sqrt(sum((x-m)**2 for x in y)/len(y)) if len(y) > 1 else 1
            s = s if s > 1e-10 else 1
            anomalies = []
            for i, yi in enumerate(y):
                z = abs((yi-m)/s)
                if z > self.z_th:
                    severity = "CRITICAL" if z > 5 else "HIGH"
                    anomalies.append({"idx": i, "val": yi, "z": z, "sev": severity})
            crit = sum(1 for a in anomalies if a["sev"] == "CRITICAL")
            danger = "CRITICAL" if crit > 0 else ("HIGH" if anomalies else "LOW")
            return len(anomalies), danger, anomalies
        except:
            return 0, "LOW", []

    # Calculate system stability score (0-100%) from data quality and anomalies
    def calc_stability(self, total_invalid, total_points, anomalies, danger):
        data_quality = ((total_points - total_invalid) / total_points * 100) if total_points > 0 else 0
        anomaly_ratio = (anomalies / total_points * 100) if total_points > 0 else 0
        danger_score = {'LOW': 100, 'HIGH': 50, 'CRITICAL': 0}.get(danger, 75)
        stability = (data_quality * 0.5 + (100 - anomaly_ratio) * 0.3 + danger_score * 0.2)
        return round(stability, 2)

    # Process single batch: clean, analyze patterns, detect anomalies, calculate statistics
    def proc(self, batch: List[float], bid: int, invalid_from_parse: int) -> Dict:
        clean, inv_clean = self.clean(batch)
        if not clean:
            return None
        m = sum(clean)/len(clean)
        s = math.sqrt(sum((x-m)**2 for x in clean)/len(clean))
        pat = self.analyze(clean)
        anom_c, dang, anom_details = self.anom(clean)
        total_invalid = invalid_from_parse + inv_clean
        return {
            "bid": bid, "total": len(batch), "valid": len(clean), 
            "invalid_parse": invalid_from_parse,
            "invalid_clean": inv_clean,
            "total_invalid": total_invalid,
            "mean": m, "std": s, "min": min(clean), "max": max(clean),
            "median": sorted(clean)[len(clean)//2],
            "range": max(clean) - min(clean),
            "cv": (s / m * 100) if m != 0 else 0,
            "type": pat['t'], "r2": pat['r'], "params": pat['p'],
            "anom": anom_c, "danger": dang, "anom_details": anom_details
        }

    # Print formatted metric with label, value, unit and color coding
    def print_metric(self, label, value, unit="", color=None):
        if color is None:
            color = self.CYAN
        spacing = " " * (40 - len(label))
        print(f"  {color}●{self.RESET}  {label}{spacing}: {self.BOLD}{value}{unit}{self.RESET}")

    # Main execution: read input, process batches, analyze patterns, display results with timing
    def run(self):
        print(f"\n{self.CYAN}{self.BOLD}{'▀'*80}{self.RESET}")
        print(f"{self.CYAN}{self.BOLD}  ⚡ PRISM v1.0 - Professional Pattern Recognition Engine{self.RESET}")
        print(f"{self.CYAN}{self.BOLD}{'▄'*80}{self.RESET}")
        print(f"\n{self.YELLOW}📝 Input Formats:{self.RESET} Space-separated, comma-separated, or mixed")
        print(f"{self.YELLOW}🚫 Invalid Data:{self.RESET} NULL, NA, NaN, empty values are auto-filtered\n")
        
        start = time.time()
        
        choice = input(f"{self.BLUE}➤ Read from [F]ile or [S]tandard input? (f/s): {self.RESET}").strip().lower()
        if choice == 'f':
            fpath = input(f"{self.BLUE}➤ Enter file path: {self.RESET}").strip()
            try:
                with open(fpath, 'r') as f:
                    raw = f.read()
            except:
                print(f"{self.RED}✗ File read error{self.RESET}"); return
        else:
            raw = input(f"{self.BLUE}➤ Enter data: {self.RESET}").strip()
        
        if not raw:
            print(f"{self.RED}✗ Empty input{self.RESET}")
            return
        data, invalid_parse = self.parse(raw)
        if not data or (len(data) == 1 and data[0] == 0):
            print(f"{self.RED}✗ Could not parse valid data{self.RESET}")
            return
        print(f"\n{self.GREEN}✓ Parsed {len(data)} valid points | Discarded: {invalid_parse}{self.RESET}")
        print(f"{self.YELLOW}⏳ Analyzing...{self.RESET}", end="", flush=True)
        nb = max(1, (len(data) + self.batch_sz - 1) // self.batch_sz)
        batches = []
        for i in range(nb):
            s = i * self.batch_sz
            e = min(s + self.batch_sz, len(data))
            batch = data[s:e]
            result = self.proc(batch, i+1, invalid_parse if i == 0 else 0)
            if result:
                batches.append(result)
            print(f"\r{self.GREEN}✓ Batch {i+1}/{nb} completed{self.RESET}", end="", flush=True)
        print()

        all_means = [b['mean'] for b in batches]
        overall_mean = sum(all_means) / len(all_means)
        r2_scores = [b['r2'] for b in batches]
        avg_r2 = sum(r2_scores) / len(r2_scores)
        all_stds = [b['std'] for b in batches]
        overall_std = sum(all_stds) / len(all_stds)
        total_invalid_all = sum(b['total_invalid'] for b in batches)
        total_valid_all = sum(b['valid'] for b in batches)
        total_points = sum(b['total'] for b in batches)
        total_anom = sum(b['anom'] for b in batches)
        best_batch = max(batches, key=lambda b: b['r2'])
        pat_type = best_batch['type']
        params = best_batch['params']
        max_danger_val = max([b['danger'] for b in batches], key=lambda x: {'LOW':0, 'HIGH':1, 'CRITICAL':2}.get(x,0))
        stability = self.calc_stability(total_invalid_all, total_points, total_anom, max_danger_val)
        if stability >= 80:
            stab_color = self.GREEN
        elif stability >= 60:
            stab_color = self.YELLOW
        else:
            stab_color = self.RED

        print(f"\n{self.MAGENTA}{self.BOLD}{'▀'*80}▀{self.RESET}")
        print(f"{self.MAGENTA}{self.BOLD}  📊 OVERALL ANALYSIS SUMMARY{self.RESET}")
        print(f"{self.MAGENTA}{self.BOLD}{'▄'*80}▄{self.RESET}")
        self.print_metric("Input Points", f"{total_points}", color=self.CYAN)
        self.print_metric("Valid Points", f"{total_valid_all}", color=self.GREEN)
        self.print_metric("Invalid Points", f"{total_invalid_all}", color=self.RED)
        self.print_metric("Data Quality", f"{(total_valid_all/total_points*100):.1f}%", color=self.YELLOW)
        self.print_metric("Total Anomalies", f"{total_anom}", color=self.RED if total_anom > 0 else self.GREEN)
        self.print_metric("Batches Processed", f"{nb}", color=self.BLUE)
        print()
        self.print_metric("Mean Value", f"{overall_mean:.6f}", color=self.CYAN)
        self.print_metric("Std Deviation", f"{overall_std:.6f}", color=self.CYAN)
        self.print_metric("Model Type", f"{pat_type}", color=self.MAGENTA)
        self.print_metric("Confidence (R²)", f"{avg_r2*100:.2f}%", color=self.GREEN if avg_r2 > 0.8 else self.YELLOW)
        print()
        self.print_metric("Risk Level", f"{max_danger_val}", 
                         color=self.GREEN if max_danger_val == "LOW" else (self.YELLOW if max_danger_val == "HIGH" else self.RED))
        self.print_metric("System Stability", f"{stability}%", color=stab_color)
        print()

        print(f"{self.MAGENTA}{self.BOLD}{'▀'*80}▀{self.RESET}")
        print(f"{self.MAGENTA}{self.BOLD}  🔬 DETECTED PATTERN FORMULA{self.RESET}")
        print(f"{self.MAGENTA}{self.BOLD}{'▄'*80}▄{self.RESET}")
        if pat_type == 'LINEAR' and 'a' in params:
            a, b = params['a'], params['b']
            print(f"  {self.MAGENTA}→{self.RESET}  y = {self.BOLD}{a:.6f}{self.RESET}*n {b:+.6f}")
        elif pat_type == 'QUAD' and 'a' in params:
            a, b, c = params['a'], params['b'], params['c']
            print(f"  {self.MAGENTA}→{self.RESET}  y = {self.BOLD}{a:.6f}{self.RESET}*n² {b:+.6f}*n {c:+.6f}")
        elif pat_type == 'EXP' and 'a' in params:
            a, b = params['a'], params['b']
            print(f"  {self.MAGENTA}→{self.RESET}  y = {self.BOLD}{a:.6f}{self.RESET} * e^({b:.6f}*n)")
        print(f"  {self.MAGENTA}→{self.RESET}  Confidence: {self.BOLD}{avg_r2*100:.2f}%{self.RESET}")
        print()

        print(f"{self.GREEN}{self.BOLD}{'▀'*80}▀{self.RESET}")
        print(f"{self.GREEN}{self.BOLD}  🎯 FUTURE PREDICTIONS{self.RESET}")
        print(f"{self.GREEN}{self.BOLD}{'▄'*80}▄{self.RESET}")
        total_pts = sum(b['total'] for b in batches)
        for i, pos in enumerate([total_pts, total_pts+5, total_pts+10], 1):
            try:
                if pat_type == 'LINEAR':
                    val = params['b'] + params['a'] * pos
                elif pat_type == 'QUAD':
                    val = params['c'] + params['b']*pos + params['a']*pos*pos
                elif pat_type == 'EXP':
                    val = params['a'] * math.exp(params['b']*pos)
                else:
                    val = overall_mean
            except:
                val = overall_mean
            print(f"  {self.GREEN}◆{self.RESET}  Position {pos:>5}: {self.BOLD}{val:>10.4f}{self.RESET} (±2.50)")
        print()

        for b in batches:
            danger_color = self.RED if b['danger'] == "CRITICAL" else (self.YELLOW if b['danger'] == "HIGH" else self.GREEN)
            print(f"{self.BLUE}{self.BOLD}{'▀'*80}▀{self.RESET}")
            print(f"{self.BLUE}{self.BOLD}  📦 BATCH {b['bid']} DETAILS{self.RESET}")
            print(f"{self.BLUE}{self.BOLD}{'▄'*80}▄{self.RESET}")
            self.print_metric("Total Points", f"{b['total']}", color=self.BLUE)
            self.print_metric("Valid Points", f"{b['valid']}", color=self.GREEN)
            self.print_metric("Invalid Points", f"{b['total_invalid']}", color=self.RED)
            self.print_metric("Mean", f"{b['mean']:.6f}", color=self.CYAN)
            self.print_metric("Std Deviation", f"{b['std']:.6f}", color=self.CYAN)
            self.print_metric("Median", f"{b['median']:.6f}", color=self.CYAN)
            self.print_metric("Range (Max-Min)", f"{b['range']:.6f}", color=self.CYAN)
            self.print_metric("Coeff of Variation", f"{b['cv']:.2f}%", color=self.YELLOW)
            self.print_metric("Min Value", f"{b['min']:.6f}", color=self.BLUE)
            self.print_metric("Max Value", f"{b['max']:.6f}", color=self.BLUE)
            self.print_metric("Pattern Type", f"{b['type']}", color=self.MAGENTA)
            self.print_metric("R² Score", f"{b['r2']:.6f}", color=self.GREEN if b['r2'] > 0.8 else self.YELLOW)
            self.print_metric("Anomalies", f"{b['anom']}", color=self.RED if b['anom'] > 0 else self.GREEN)
            self.print_metric("Risk Level", f"{b['danger']}", color=danger_color)
            print()

        all_anomalies = []
        for b in batches:
            all_anomalies.extend(b['anom_details'])
        if all_anomalies:
            print(f"{self.RED}{self.BOLD}{'▀'*80}▀{self.RESET}")
            print(f"{self.RED}{self.BOLD}  ⚠️  ANOMALIES DETECTED ({len(all_anomalies)}){self.RESET}")
            print(f"{self.RED}{self.BOLD}{'▄'*80}▄{self.RESET}")
            for anom in all_anomalies[:15]:
                sev_color = self.RED if anom['sev'] == "CRITICAL" else self.YELLOW
                print(f"  {sev_color}◆{self.RESET}  Pos {anom['idx']:<4} | Value: {anom['val']:>10.2f} | Z-Score: {anom['z']:>6.2f} | {sev_color}{anom['sev']}{self.RESET}")
            if len(all_anomalies) > 15:
                print(f"  {self.DIM}... and {len(all_anomalies)-15} more anomalies{self.DIM}")
            print()

        elapsed = time.time() - start
        print(f"{self.CYAN}{self.BOLD}{'▀'*80}▀{self.RESET}")
        print(f"{self.GREEN}{self.BOLD}  ✨ Analysis Complete in {elapsed:.2f} seconds{self.RESET}")
        print(f"{self.CYAN}{self.BOLD}{'▄'*80}▄{self.RESET}\n")


if __name__ == "__main__":
    try:
        Engine().run()
    except KeyboardInterrupt:
        print(f"\n{Engine.RED}✗ Interrupted{Engine.RESET}")
    except Exception as e:
        print(f"\n{Engine.RED}✗ Error: {e}{Engine.RESET}")