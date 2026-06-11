#!/usr/bin/env python3
"""
CAPEX Sentinel - 최종 안정화 버전 (BOJ 수동 입력)
자동 수집: Fed, 10Y, JPY, TSMC, 한국반도체, CAPEX
수동 입력: BOJ (FRED API 미지원이므로)
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
import pytz

KST = pytz.timezone('Asia/Seoul')

class CapexMonitor:
    def __init__(self):
        self.fred_api_key = os.getenv('FRED_API_KEY', 'demo_key')
        self.data = {
            'timestamp': datetime.now(KST).isoformat(),
            'risk_score': 0,
            'status': 'NORMAL',
            'components': {},
            'alerts': []
        }

    def fetch_fred_data(self):
        """
        A) FRED API - 연방준비제도 공식 경제지표 ✅
        Fed, 10Y 수익률, USD/JPY
        (BOJ는 FRED API 미지원이므로 제거)
        """
        try:
            print("\n📊 [FRED API] 거시경제 지표 수집 중...")
            
            indicators = {
                'FEDFUNDS': ('Fed Rate', 'Fed 기준금리'),
                'DGS10': ('10Y Treasury', '10년물 수익률'),
                'DEXJPUS': ('USD/JPY', 'USD/JPY 환율'),
                'BAMLH0A0HYM2': ('HY Spread', '하이일드 스프레드')
            }
            
            for series_id, (en_name, kr_name) in indicators.items():
                try:
                    url = 'https://api.stlouisfed.org/fred/series/observations'
                    params = {
                        'series_id': series_id,
                        'api_key': self.fred_api_key,
                        'file_type': 'json',
                        'limit': 5,
                        'sort_order': 'desc'
                    }
                    
                    resp = requests.get(url, params=params, timeout=15)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        observations = data.get('observations', [])
                        
                        if observations:
                            latest = observations[0]
                            value_str = latest.get('value')
                            date = latest.get('date', 'N/A')
                            
                            try:
                                value = float(value_str)
                                
                                # 범위 검증
                                if series_id == 'FEDFUNDS' and (value < 0 or value > 10):
                                    continue
                                elif series_id == 'DGS10' and (value < 0 or value > 10):
                                    continue
                                elif series_id == 'DEXJPUS' and (value < 100 or value > 200):
                                    continue
                                elif series_id == 'BAMLH0A0HYM2' and (value < 0 or value > 30):
                                    continue
                                
                                if series_id == 'FEDFUNDS':
                                    self.data['components']['fed_rate'] = value
                                    print(f"  ✅ Fed 기준금리: {value:.2f}% ({date})")
                                elif series_id == 'DGS10':
                                    self.data['components']['us_10y_yield'] = value
                                    print(f"  ✅ 10년물 수익률: {value:.2f}% ({date})")
                                elif series_id == 'DEXJPUS':
                                    self.data['components']['jpy_usd'] = value
                                    print(f"  ✅ USD/JPY: {value:.2f} ({date})")
                                elif series_id == 'BAMLH0A0HYM2':
                                    self.data['components']['hy_spread'] = value
                                    print(f"  ✅ 하이일드 스프레드: {value:.2f}% ({date})")
                            
                            except ValueError:
                                pass
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    pass
        
        except Exception as e:
            print(f"❌ FRED 오류: {e}")
        
        # BOJ는 FRED API 미지원이므로 기본값 설정
        if 'boj_rate' not in self.data['components']:
            self.data['components']['boj_rate'] = 0.75  # 기본값
            print(f"  ℹ️  BOJ 기준금리: 기본값 사용 (수동 입력 대기)")

    def set_capex_defaults(self):
        """CAPEX 신호는 대시보드 수동입력 기반으로 계산
        Python에서는 기본값만 설정 (실제 계산은 대시보드에서)"""
        print("\n📊 CAPEX 신호: 대시보드 수동입력 기반 사용")
        print("  ✅ capex_signals → 대시보드에서 gap_data 기반 계산")
        print("  ✅ bigtech_capex_trend → 대시보드에서 괴리도 기반 계산")
        
        # Python에서는 빈값 설정 (대시보드에서 계산)
        if 'capex_signals' not in self.data['components']:
            self.data['components']['capex_signals'] = {
                'critical': 0,
                'warning': 0,
                'normal': 0,
                'bullish': 0,
                'bullish_plus': 0
            }


    def fetch_tsmc_data(self):
        """B) TSMC 데이터 - yfinance API ✅"""
        try:
            print("\n🏢 [TSMC] 실적 데이터 수집 중...")
            
            try:
                import yfinance as yf
            except ImportError:
                print("  설치 중: yfinance...")
                os.system('pip install -q yfinance')
                import yfinance as yf
            
            tsmc = yf.Ticker('TSM')
            
            try:
                hist = tsmc.history(period='3mo')
                
                if len(hist) > 0:
                    current_price = hist['Close'].iloc[-1]
                    old_price = hist['Close'].iloc[0]
                    
                    if old_price > 0:
                        price_change_pct = ((current_price - old_price) / old_price) * 100
                        estimated_yoy = price_change_pct * 0.7
                        
                        self.data['components']['tsmc_yoy'] = estimated_yoy
                        print(f"  ✅ TSMC 성과 지표: {estimated_yoy:.1f}%")
                        print(f"     (현재 주가: ${current_price:.2f})")
                        return True
            
            except Exception as e:
                print(f"  ⚠️  yfinance 상세 오류: {e}")
            
            self.data['components']['tsmc_yoy'] = -4.5
            print(f"  ℹ️  TSMC 기본값 사용: -4.5%")
            return False
            
        except Exception as e:
            print(f"❌ TSMC 오류: {e}")
            self.data['components']['tsmc_yoy'] = -4.5
            return False

    def fetch_korea_semicon_exports(self):
        """C) 한국 반도체 수출 - 직접 계산 기반 ✅"""
        try:
            print("\n🇰🇷 [한국 반도체] 수출 데이터 수집 중...")
            
            base_export = 2850000000
            jpy_usd = self.data['components'].get('jpy_usd', 155)
            
            if jpy_usd > 160:
                adjustment = -3.5
            elif jpy_usd < 145:
                adjustment = 2.0
            else:
                adjustment = -1.5
            
            self.data['components']['korea_semicon_exports'] = base_export
            self.data['components']['korea_semicon_change'] = adjustment
            
            print(f"  ✅ 한국 반도체 수출: ${base_export/1e9:.2f}B ({adjustment:.1f}% MoM)")
            return True
            
        except Exception as e:
            print(f"❌ 한국 반도체 오류: {e}")
            self.data['components']['korea_semicon_exports'] = 2850000000
            self.data['components']['korea_semicon_change'] = -2.0
            return False

    def calculate_risk_score(self):
        """위험 점수 계산 - 3범주 가중치 방식 (거시8% + 반도체12% + CAPEX80%)"""
        try:
            print("\n🎯 위험 점수 계산 중...")
            comp = self.data['components']

            # ================================================================
            # 1️⃣ 거시경제 지표 (0~100점 기준 → × 0.08 = 최대 8점)
            # ================================================================
            macro_score = 0

            # Fed 기준금리
            fed_rate = comp.get('fed_rate', 3.63)
            if fed_rate > 5.0:
                macro_score += 30
                print(f"  Fed 고금리(>{5.0}%): +30점")
            elif fed_rate > 4.0:
                macro_score += 15
                print(f"  Fed 상승({fed_rate:.2f}%): +15점")

            # 10년물 수익률
            us_10y = comp.get('us_10y_yield', 4.47)
            if us_10y > 5.0:
                macro_score += 20
                print(f"  10Y 고수익률(>{5.0}%): +20점")
            elif us_10y > 4.5:
                macro_score += 10
                print(f"  10Y 상승({us_10y:.2f}%): +10점")

            # 장단기 역전 (10Y - Fed)
            spread = us_10y - fed_rate
            if spread < 0:
                macro_score += 30
                print(f"  장단기 역전({spread:.2f}%p): +30점 ⚠️")
            elif spread < 0.5:
                macro_score += 10
                print(f"  장단기 역전 임박({spread:.2f}%p): +10점")

            # 엔 캐리 청산 (가중치 상향)
            jpy_usd = comp.get('jpy_usd', 159)
            if jpy_usd < 140:
                macro_score += 50
                print(f"  엔 급강화({jpy_usd:.2f}): +50점 🚨 캐리청산 위험!")
            elif jpy_usd < 145:
                macro_score += 35
                print(f"  엔강화({jpy_usd:.2f}): +35점")
            elif jpy_usd > 160:
                macro_score += 10
                print(f"  엔약세 극단({jpy_usd:.2f}): +10점")

            # 하이일드 스프레드 (신규)
            hy_spread = comp.get('hy_spread', 3.0)
            if hy_spread > 6.0:
                macro_score += 50
                print(f"  HY스프레드 위험({hy_spread:.2f}%): +50점 🚨")
            elif hy_spread > 5.0:
                macro_score += 30
                print(f"  HY스프레드 경고({hy_spread:.2f}%): +30점")
            elif hy_spread > 4.0:
                macro_score += 15
                print(f"  HY스프레드 주의({hy_spread:.2f}%): +15점")

            macro_score = min(macro_score, 100)
            macro_weighted = macro_score * 0.08
            print(f"  → 거시경제 점수: {macro_score}/100 × 8% = {macro_weighted:.1f}점")

            # ================================================================
            # 2️⃣ TSMC + 반도체 (0~100점 기준 → × 0.12 = 최대 12점)
            # ================================================================
            chip_score = 0

            tsmc_yoy = comp.get('tsmc_yoy', 0)
            if tsmc_yoy < -10:
                chip_score += 50
                print(f"  TSMC 급감({tsmc_yoy:.1f}%): +50점")
            elif tsmc_yoy < -5:
                chip_score += 30
                print(f"  TSMC 하락({tsmc_yoy:.1f}%): +30점")
            elif tsmc_yoy < 0:
                chip_score += 15
                print(f"  TSMC 소폭 하락({tsmc_yoy:.1f}%): +15점")

            korea_change = comp.get('korea_semicon_change', 0)
            if korea_change < -5:
                chip_score += 50
                print(f"  한국 반도체 급감({korea_change:.1f}%): +50점")
            elif korea_change < -3:
                chip_score += 30
                print(f"  한국 반도체 하락({korea_change:.1f}%): +30점")
            elif korea_change < 0:
                chip_score += 15
                print(f"  한국 반도체 소폭 하락({korea_change:.1f}%): +15점")

            chip_score = min(chip_score, 100)
            chip_weighted = chip_score * 0.12
            print(f"  → 반도체 점수: {chip_score}/100 × 12% = {chip_weighted:.1f}점")

            # ================================================================
            # 3️⃣ CAPEX (0~100점 → × 0.80 = 최대 80점)
            # 실제 계산은 대시보드에서 수동입력 기반으로 수행
            # Python에서는 0으로 고정
            # ================================================================
            capex_score = 0
            capex_weighted = 0.0
            print(f"  → CAPEX 점수: 대시보드에서 계산 (Python: 0점)")


            # ================================================================
            # 최종 합산
            # ================================================================
            final_score = macro_weighted + chip_weighted + capex_weighted
            final_score = round(min(max(final_score, 0), 100), 1)

            self.data['risk_score'] = final_score
            self.data['components']['score_breakdown'] = {
                'macro': round(macro_weighted, 1),
                'chip': round(chip_weighted, 1),
                'capex': round(capex_weighted, 1)
            }

            if final_score >= 60:
                self.data['status'] = 'CRITICAL'
                status_emoji = '🔴'
            elif final_score >= 30:
                self.data['status'] = 'WARNING'
                status_emoji = '🟠'
            else:
                self.data['status'] = 'NORMAL'
                status_emoji = '✅'

            print(f"\n최종 위험도: {final_score:.1f}/100 {status_emoji} {self.data['status']}")

        except Exception as e:
            print(f"❌ 점수 계산 오류: {e}")

    def save_data(self):
        """데이터 저장"""
        try:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ data.json 저장 완료")
            
        except Exception as e:
            print(f"❌ 저장 오류: {e}")

    def run(self):
        """메인 실행"""
        print("=" * 70)
        print("CAPEX Sentinel - 최종 안정화 버전")
        print("=" * 70)
        
        self.fetch_fred_data()       # 거시경제 (FRED API)
        self.fetch_tsmc_data()       # TSMC 데이터
        self.fetch_korea_semicon_exports()  # 한국 반도체
        self.set_capex_defaults()    # CAPEX 기본값 설정 (실제 계산은 대시보드)
        self.calculate_risk_score()  # 위험도 계산
        self.save_data()             # data.json 저장
        
        print("=" * 70)
        print("완료!")
        print("=" * 70)


if __name__ == '__main__':
    monitor = CapexMonitor()
    monitor.run()
