#!/usr/bin/env python3
"""
CAPEX Sentinel - SEC Company Facts API v3
필드명 문제 해결 + 디버깅 로그 추가
"""

import requests
import json
import time
from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')

class SECCapexParserV3:
    def __init__(self):
        self.companies = {
            'MSFT': {'cik': '0000789019', 'name': 'Microsoft'},
            'GOOGL': {'cik': '0001652044', 'name': 'Alphabet'},
            'AMZN': {'cik': '0001018724', 'name': 'Amazon'},
            'META': {'cik': '0001326801', 'name': 'Meta'},
            'AAPL': {'cik': '0000320193', 'name': 'Apple'},
            'NVDA': {'cik': '0001045810', 'name': 'NVIDIA'},
            'TSLA': {'cik': '0001652860', 'name': 'Tesla'}
        }
        
        self.capex_data = {}
        self.headers = {
            'User-Agent': 'CAPEX Sentinel (birdjinx@gmail.com)'
        }

    def fetch_company_facts(self, ticker, cik):
        """SEC Company Facts API에서 데이터 추출"""
        try:
            print(f"\n  [{ticker}] SEC에서 데이터 추출 중...")
            
            # Company Facts API 호출
            url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                print(f"    ❌ API 응답 오류: {response.status_code}")
                return None
            
            data = response.json()
            
            # 가능한 모든 CAPEX 필드명들 (우선순위순)
            capex_fields = [
                'us-gaap:PaymentsForCapitalExpenditures',      # 가장 일반적
                'us-gaap:CapitalExpenditures',
                'us-gaap:PropertyPlantAndEquipmentPurchases',
                'us-gaap:CapitalExpenditure'
            ]
            
            # us-gaap 섹션에서 필드 찾기
            us_gaap = data.get('facts', {}).get('us-gaap', {})
            
            capex_values = None
            used_field = None
            
            # 각 필드명 시도
            for field in capex_fields:
                if field in us_gaap:
                    capex_values = us_gaap[field]
                    used_field = field
                    print(f"    ✅ 필드 찾음: {field}")
                    break
            
            if not capex_values:
                print(f"    ⚠️  CAPEX 필드 없음. 사용 가능한 필드들:")
                # 사용 가능한 필드 목록 출력 (디버깅)
                available_fields = list(us_gaap.keys())
                for f in available_fields[:5]:  # 처음 5개만
                    if 'capital' in f.lower() or 'expenditure' in f.lower() or 'property' in f.lower():
                        print(f"       → {f}")
                return None
            
            # 10-Q (분기보고)에서 최신 데이터 추출
            quarterly_capex = []
            
            for entry in capex_values:
                form = entry.get('form', '')
                value = entry.get('val')
                date = entry.get('filed')
                
                # 10-Q만 선택
                if form == '10-Q' and value and date:
                    # 값을 백만 달러 단위로 변환
                    # SEC 데이터는 보통 달러 단위
                    if value > 10000:
                        capex_m = int(value / 1e6)
                    else:
                        capex_m = int(value)
                    
                    quarterly_capex.append({
                        'date': date,
                        'capex': capex_m,
                        'form': form
                    })
            
            if not quarterly_capex:
                print(f"    ⚠️  10-Q 분기보고 데이터 없음")
                # 10-K (연간보고)도 시도
                for entry in capex_values:
                    if entry.get('form') == '10-K' and entry.get('val') and entry.get('filed'):
                        value = entry.get('val')
                        if value > 10000:
                            capex_m = int(value / 1e6)
                        else:
                            capex_m = int(value)
                        
                        quarterly_capex.append({
                            'date': entry.get('filed'),
                            'capex': capex_m,
                            'form': '10-K'
                        })
                
                if not quarterly_capex:
                    print(f"    ❌ 데이터 없음")
                    return None
            
            # 날짜순 정렬
            quarterly_capex.sort(key=lambda x: x['date'], reverse=True)
            
            # 최근 4개
            recent = quarterly_capex[:4]
            
            print(f"    ✅ {len(recent)}개 분기 데이터 확보:")
            for q in recent:
                print(f"       {q['date']}: ${q['capex']}M ({q['form']})")
            
            return recent
            
        except Exception as e:
            print(f"    ❌ 오류: {e}")
            return None

    def process_quarters(self, ticker, quarterly_data):
        """QoQ 계산"""
        try:
            if not quarterly_data or len(quarterly_data) < 2:
                return None
            
            sorted_data = sorted(quarterly_data, key=lambda x: x['date'])
            
            processed = []
            for i, data in enumerate(sorted_data):
                date = data['date']
                month = int(date[5:7])
                year = int(date[0:4])
                
                if month in [2, 3]:
                    quarter = f"Q1 {year}"
                elif month in [5, 6]:
                    quarter = f"Q2 {year}"
                elif month in [8, 9]:
                    quarter = f"Q3 {year}"
                else:
                    quarter = f"Q4 {year}"
                
                capex = data['capex']
                
                if i > 0:
                    prev_capex = sorted_data[i-1]['capex']
                    qoq = ((capex - prev_capex) / prev_capex) * 100 if prev_capex > 0 else 0
                else:
                    qoq = 0
                
                processed.append({
                    'quarter': quarter,
                    'capex': capex,
                    'qoq': qoq,
                    'date': date
                })
            
            return processed
            
        except Exception as e:
            print(f"    ❌ 처리 오류: {e}")
            return None

    def run(self):
        """전체 실행"""
        print("=" * 70)
        print("SEC Company Facts API v3 - 실제 CAPEX 파싱")
        print("=" * 70)
        
        for ticker, info in self.companies.items():
            try:
                quarterly_data = self.fetch_company_facts(ticker, info['cik'])
                
                if not quarterly_data:
                    continue
                
                processed = self.process_quarters(ticker, quarterly_data)
                
                if processed:
                    self.capex_data[ticker] = {
                        'name': info['name'],
                        'quarters': processed,
                        'latest_capex': processed[-1]['capex'],
                        'latest_qoq': processed[-1]['qoq'],
                        'data_source': 'SEC Company Facts API (공식 XBRL)'
                    }
                    
                    print(f"  ✓ {ticker}: 완료")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"  ❌ {ticker}: {e}")
                continue
        
        print("\n" + "=" * 70)
        print(f"최종: {len(self.capex_data)}개 기업 데이터 확보")
        print("=" * 70)
        
        self.save_data()
        self.print_results()

    def save_data(self):
        """저장"""
        try:
            output = {
                'timestamp': datetime.now(KST).isoformat(),
                'data_source': 'SEC Company Facts API',
                'capex_by_company': self.capex_data
            }
            
            with open('data_sec_capex.json', 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ data_sec_capex.json 저장")
            
        except Exception as e:
            print(f"❌ 저장 오류: {e}")

    def print_results(self):
        """결과 출력"""
        print("\n" + "=" * 70)
        print("CAPEX 데이터:")
        print("=" * 70)
        
        for ticker, data in self.capex_data.items():
            print(f"\n{ticker} ({data['name']})")
            for q in data['quarters']:
                qoq_str = f"({q['qoq']:+.1f}%)" if q['qoq'] != 0 else ""
                print(f"  {q['quarter']}: ${q['capex']}M {qoq_str}")


if __name__ == '__main__':
    parser = SECCapexParserV3()
    parser.run()
