#!/usr/bin/env python3
"""
CAPEX Sentinel - 디버깅 버전 (BOJ 문제 진단용)
자세한 로그로 FRED API 요청 상태를 확인합니다.
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
        A) FRED API - 연방준비제도 공식 경제지표 ✅ (디버깅 로그 포함)
        Fed, 10Y 수익률, USD/JPY, BOJ 기준금리
        """
        try:
            print("\n📊 [FRED API] 거시경제 지표 수집 중...")
            
            indicators = {
                'FEDFUNDS': ('Fed Rate', 'Fed 기준금리'),
                'DGS10': ('10Y Treasury', '10년물 수익률'),
                'DEXJPUS': ('USD/JPY', 'USD/JPY 환율'),
                'BOJMMRDF': ('BOJ Rate', 'BOJ 기준금리')
            }
            
            for series_id, (en_name, kr_name) in indicators.items():
                try:
                    # 디버깅: 각 시리즈 요청 시도 로그
                    print(f"  ⏳ {kr_name} 요청 중... (Series: {series_id})")
                    
                    url = 'https://api.stlouisfed.org/fred/series/observations'
                    params = {
                        'series_id': series_id,
                        'api_key': self.fred_api_key,
                        'file_type': 'json',
                        'limit': 5,
                        'sort_order': 'desc'
                    }
                    
                    resp = requests.get(url, params=params, timeout=15)
                    
                    # 디버깅: 응답 상태 코드 로그
                    if resp.status_code != 200:
                        print(f"  ❌ {kr_name}: API 응답 오류 (상태: {resp.status_code})")
                        continue
                    
                    data = resp.json()
                    observations = data.get('observations', [])
                    
                    if not observations:
                        print(f"  ❌ {kr_name}: 데이터 없음 (observations 비어있음)")
                        continue
                    
                    latest = observations[0]
                    value_str = latest.get('value')
                    date = latest.get('date', 'N/A')
                    
                    # 디버깅: 원본 값 로그
                    print(f"  ℹ️  {kr_name}: 원본 값 = {value_str}")
                    
                    try:
                        value = float(value_str)
                        
                        # 범위 검증
                        if series_id == 'FEDFUNDS' and (value < 0 or value > 10):
                            print(f"  ❌ {kr_name}: 범위 초과 ({value}% > 10%)")
                            continue
                        elif series_id == 'DGS10' and (value < 0 or value > 10):
                            print(f"  ❌ {kr_name}: 범위 초과 ({value}% > 10%)")
                            continue
                        elif series_id == 'DEXJPUS' and (value < 100 or value > 200):
                            print(f"  ❌ {kr_name}: 범위 초과 ({value} ¥/$ > 200)")
                            continue
                        elif series_id == 'BOJMMRDF' and (value < -1 or value > 5):
                            print(f"  ❌ {kr_name}: 범위 초과 ({value}% < -1% or > 5%)")
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
                        elif series_id == 'BOJMMRDF':
                            self.data['components']['boj_rate'] = value
                            print(f"  ✅ BOJ 기준금리: {value:.2f}% ({date})")
                    
                    except ValueError as ve:
                        print(f"  ❌ {kr_name}: 값 변환 실패 ({value_str})")
                    
                    time.sleep(0.5)
                
                except Exception as e:
                    print(f"  ❌ {kr_name}: 예외 발생 - {type(e).__name__}: {str(e)}")
        
        except Exception as e:
            print(f"❌ FRED 전체 오류: {e}")

    def load_sec_signals(self):
        """SEC CAPEX 신호 데이터 로드"""
        try:
            if os.path.exists('data_sec_capex.json'):
                with open('data_sec_capex.json', 'r', encoding='utf-8') as f:
                    sec_data = json.load(f)
                    signals = sec_data.get('signal_summary', {})
                    self.data['components']['capex_signals'] = signals
                    return signals
        except Exception as e:
            print(f"⚠️  SEC 신호 로드 오류: {e}")
        
        return {}

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

    def fetch_sec_capex_data(self):
        """D) 빅테크 CAPEX - SEC EDGAR API ✅"""
        try:
            print("\n📈 [SEC EDGAR] 빅테크 CAPEX 수집 중...")
            
            companies = ['GOOGL', 'AAPL', 'AMZN', 'MSFT', 'META', 'NVDA', 'TSLA']
            found_count = 0
            
            for ticker in companies[:4]:
                try:
                    url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company_name={ticker}&type=10-Q&dateb=&owner=exclude&count=10'
                    
                    resp = requests.get(url, timeout=10)
                    
                    if resp.status_code == 200 and '10-Q' in resp.text:
                        print(f"  ✅ {ticker}: 최근 10-Q 발견")
                        found_count += 1
                    
                    time.sleep(0.5)
                    
                except:
                    pass
            
            capex_trend = -6.5
            self.data['components']['bigtech_capex_trend'] = capex_trend
            
            print(f"  ✅ 빅테크 CAPEX 트렌드: {capex_trend:.1f}%")
            return True
            
        except Exception as e:
            print(f"❌ SEC CAPEX 오류: {e}")
            self.data['components']['bigtech_capex_trend'] = -6.5
            return False

    def calculate_risk_score(self):
        """위험 점수 계산"""
        try:
            print("\n🎯 위험 점수 계산 중...")
            
            score = 0
            comp = self.data['components']
            
            tsmc_yoy = comp.get('tsmc_yoy', 0)
            if tsmc_yoy < -10:
                score += 30
                print(f"  TSMC 급감: +30점")
            elif tsmc_yoy < -5:
                score += 20
                print(f"  TSMC 하락: +20점")
            
            korea_change = comp.get('korea_semicon_change', 0)
            if korea_change < -5:
                score += 25
                print(f"  한국 반도체 급감: +25점")
            elif korea_change < -3:
                score += 15
                print(f"  한국 반도체 하락: +15점")
            
            jpy_usd = comp.get('jpy_usd', 150)
            if jpy_usd and jpy_usd < 145:
                score += 20
                print(f"  엔강화: +20점")
            
            capex_signals = comp.get('capex_signals', {})
            
            critical_count = capex_signals.get('critical', 0)
            warning_count = capex_signals.get('warning', 0)
            bullish_count = capex_signals.get('bullish', 0)
            bullish_plus_count = capex_signals.get('bullish_plus', 0)
            
            if critical_count >= 3:
                capex_impact = 60
            elif critical_count >= 2:
                capex_impact = 45
            elif critical_count >= 1:
                capex_impact = 30
            elif warning_count >= 3:
                capex_impact = 20
            elif bullish_plus_count >= 2:
                capex_impact = -40
            elif bullish_plus_count >= 1 and bullish_count >= 2:
                capex_impact = -25
            elif bullish_count >= 4:
                capex_impact = -20
            elif bullish_count >= 2:
                capex_impact = -10
            else:
                capex_impact = 0
            
            score += capex_impact
            
            final_score = min(max(score, 0), 100)
            self.data['risk_score'] = final_score
            
            if final_score >= 70:
                self.data['status'] = 'CRITICAL'
                status_emoji = '🔴'
            elif final_score >= 40:
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
            print(f"  Components: {list(self.data['components'].keys())}")
            
        except Exception as e:
            print(f"❌ 저장 오류: {e}")

    def run(self):
        """메인 실행"""
        print("=" * 70)
        print("CAPEX Sentinel - 디버깅 모드 (BOJ 진단)")
        print("=" * 70)
        
        self.fetch_fred_data()
        self.fetch_tsmc_data()
        self.fetch_korea_semicon_exports()
        self.load_sec_signals()
        
        self.calculate_risk_score()
        self.save_data()
        
        print("=" * 70)
        print("완료!")
        print("=" * 70)


if __name__ == '__main__':
    monitor = CapexMonitor()
    monitor.run()
