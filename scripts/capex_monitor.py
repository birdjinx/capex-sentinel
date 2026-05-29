#!/usr/bin/env python3
"""
CAPEX Sentinel - 금융 조기경보 시스템
"""

import os
import json
import requests
from datetime import datetime
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
        """FRED API에서 데이터 가져오기"""
        try:
            print("📊 FRED 데이터 수집 중...")
            indicators = {
                'DGS10': 'US 10Y Treasury Yield',
                'DEXJPUS': 'USD/JPY Exchange Rate',
                'FEDFUNDS': 'Federal Funds Rate'
            }
            
            for series_id, name in indicators.items():
                url = f'https://api.stlouisfed.org/fred/series/observations'
                params = {
                    'series_id': series_id,
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'limit': 1
                }
                
                try:
                    resp = requests.get(url, params=params, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get('observations'):
                            value = float(data['observations'][0].get('value', 0))
                            print(f"✓ {name}: {value}")
                            
                            if series_id == 'DGS10':
                                self.data['components']['us_10y_yield'] = value
                            elif series_id == 'DEXJPUS':
                                self.data['components']['jpy_usd'] = value
                            elif series_id == 'FEDFUNDS':
                                self.data['components']['fed_rate'] = value
                except Exception as e:
                    print(f"⚠️ {series_id} 실패: {e}")
                    
        except Exception as e:
            print(f"❌ FRED 오류: {e}")

    def fetch_sample_data(self):
        """샘플 데이터 (데모용)"""
        print("📈 샘플 데이터 생성 중...")
        
        self.data['components']['tsmc_yoy'] = -8.5
        self.data['components']['korea_semicon_exports'] = 2850000000
        self.data['components']['korea_semicon_change'] = -5.3
        self.data['components']['bigtech_capex_trend'] = -7.2
        
        if not self.data['components'].get('jpy_usd'):
            self.data['components']['jpy_usd'] = 150.0
        if not self.data['components'].get('fed_rate'):
            self.data['components']['fed_rate'] = 5.25

    def calculate_risk_score(self):
        """위험 점수 계산"""
        print("🎯 위험 점수 계산 중...")
        
        score = 0
        
        tsmc_yoy = self.data['components'].get('tsmc_yoy', 0)
        if tsmc_yoy < -10:
            score += 30
        elif tsmc_yoy < -5:
            score += 20
        
        korea_change = self.data['components'].get('korea_semicon_change', 0)
        if korea_change < -5:
            score += 25
        elif korea_change < -3:
            score += 15
        
        capex_trend = self.data['components'].get('bigtech_capex_trend', 0)
        if capex_trend < -10:
            score += 25
        elif capex_trend < -5:
            score += 15
        
        jpy_usd = self.data['components'].get('jpy_usd', 150)
        if jpy_usd < 145:
            score += 20
        
        final_score = min(max(score, 0), 100)
        self.data['risk_score'] = final_score
        
        if final_score >= 70:
            self.data['status'] = 'CRITICAL'
        elif final_score >= 40:
            self.data['status'] = 'WARNING'
        else:
            self.data['status'] = 'NORMAL'
        
        print(f"✓ 최종 점수: {final_score} ({self.data['status']})")

    def save_data(self):
        """data.json에 저장"""
        try:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            print("✓ data.json 저장 완료")
        except Exception as e:
            print(f"❌ 저장 오류: {e}")

    def run(self):
        """메인 실행"""
        print("=" * 50)
        print("CAPEX Sentinel 시작")
        print("=" * 50)
        
        self.fetch_fred_data()
        self.fetch_sample_data()
        self.calculate_risk_score()
        self.save_data()
        
        print("=" * 50)
        print("완료!")
        print("=" * 50)

if __name__ == '__main__':
    monitor = CapexMonitor()
    monitor.run()
