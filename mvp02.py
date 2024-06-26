import streamlit as st
import folium
from streamlit_folium import folium_static
import os
from openai import OpenAI
import google.generativeai as genai
import json
import re
import logging
import random

print(os.getcwd())

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# Streamlit secrets에서 OpenAI API 키 가져오기
OPENAI_API_KEY = st.secrets["OPENAI"]["api_key"]
GOOGLE_API_KEY = st.secrets["GOOGLE"]["api_key"]

# OpenAI 클라이언트 설정
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Google Gemini 설정
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# 페이지 설정
st.set_page_config(page_title="도쿄 맛집 추천 서비스", layout="wide")

# 제목
st.title("도쿄 맛집 추천 서비스")

# 사이드바 설정
st.sidebar.header("검색 옵션")

# 위치 선택
locations = {
    "신주쿠": "shinjuku",
    "시부야": "shibuya",
    "긴자": "ginza",
    "롯폰기": "roppongi",
    "우에노": "ueno"
}
location = st.sidebar.selectbox("도쿄 내 관광지 선택", list(locations.keys()))

# 메뉴 선택
menus = {
    "스시": "sushi",
    "라멘": "ramen",
    "야키토리": "yakitori",
    "텐푸라": "tempura",
    "우동": "udon"
}
menu = st.sidebar.selectbox("도쿄 대표 메뉴 선택", list(menus.keys()))

# API 선택
api_choice = st.sidebar.radio("사용할 API 선택", ["OpenAI GPT", "Google Gemini"])

def extract_json(text):
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        return match.group()
    return None

def call_openai_api(location, menu):
    prompt = f"""tabelog.com 사이트를 기반으로 도쿄의 {location} 지역에 위치한 현재 영업 중인 {menu} 맛집을 추천해주세요. 
    별점 5점에 가까운 랭킹 1위~5위 맛집을 선정하고, 각 맛집에 대해 다음 정보를 포함해 주세요:
    - 가게 이름
    - 별점 (5점 만점)
    - 리뷰 수
    - 가게 리뷰 요약
    - 상세 정보 (특징, 추천 메뉴 등)
    - 가게 정보 (주소, 전화번호, 영업시간, 가격대)
    - 추천 이유
 

    반드시 다음과 같은 유효한 JSON 형식으로 응답해주세요:
    [
      {{
        "name": "레스토랑 이름",
        "rating": 4.5,
        "reviews": 100,
        "review_summary": "리뷰 요약",
        "details": "상세 정보",
        "address": "주소",
        "phone": "전화번호",
        "hours": "영업시간",
        "price_range": "가격대",
        "reason": "추천 이유"
      }},
      ...
    ]
    """

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 도쿄 레스토랑 추천 전문가입니다."},
            {"role": "user", "content": prompt}
        ]
    )
    
    logging.info(f"OpenAI API 원본 응답: {response.choices[0].message.content}")
    
    json_str = extract_json(response.choices[0].message.content)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류: {str(e)}")
            return None
    else:
        logging.error("응답에서 JSON을 찾을 수 없습니다.")
        return None

def call_gemini_api(location, menu):
    prompt = f"""tabelog.com 사이트를 기반으로 도쿄의 {location} 지역에 위치한 현재 영업 중인 {menu} 맛집을 추천해주세요. 
    별점 5점에 가까운 랭킹 1위~5위 맛집을 선정하고, 각 맛집에 대해 다음 정보를 포함해 주세요:
    - 가게 이름
    - 별점 (5점 만점)
    - 리뷰 수
    - 가게 리뷰 요약
    - 상세 정보 (특징, 추천 메뉴 등)
    - 가게 정보 (주소, 전화번호, 영업시간, 가격대)
    - 추천 이유
    

    반드시 다음과 같은 유효한 JSON 형식으로 응답해주세요:
    [
      {{
        "name": "레스토랑 이름",
        "rating": 4.5,
        "reviews": 100,
        "review_summary": "리뷰 요약",
        "details": "상세 정보",
        "address": "주소",
        "phone": "전화번호",
        "hours": "영업시간",
        "price_range": "가격대",
        "reason": "추천 이유"
      }},
      ...
    ]
    """

    response = gemini_model.generate_content(prompt)
    
    logging.info(f"Gemini API 원본 응답: {response.text}")
    
    json_str = extract_json(response.text)
    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류: {str(e)}")
            return None
    else:
        logging.error("응답에서 JSON을 찾을 수 없습니다.")
        return None

# 검색 버튼
if st.sidebar.button("맛집 검색"):
    # 지도 표시
    latitudes = {
        "신주쿠": 35.6938,
        "시부야": 35.6580,
        "긴자": 35.6721,
        "롯폰기": 35.6628,
        "우에노": 35.7089
    }
    longitudes = {
        "신주쿠": 139.7034,
        "시부야": 139.7016,
        "긴자": 139.7666,
        "롯폰기": 139.7315,
        "우에노": 139.7741
    }

    lat, lon = latitudes[location], longitudes[location]

    m = folium.Map(location=[lat, lon], zoom_start=15)
    folium.Marker([lat, lon], popup=location, icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

    # API 호출 및 결과 표시
    try:
        with st.spinner('맛집 정보를 가져오는 중...'):
            if api_choice == "OpenAI GPT":
                recommendations = call_openai_api(location, menu)
            else:
                recommendations = call_gemini_api(location, menu)
        
        if recommendations is None:
            st.error("맛집 정보를 가져오는 데 실패했습니다. 다시 시도해 주세요.")
        elif isinstance(recommendations, list):
            for idx, restaurant in enumerate(recommendations):
                # 임의의 위치 생성 (실제로는 각 맛집의 정확한 위치를 사용해야 합니다)
                restaurant_lat = lat + random.uniform(-0.005, 0.005)
                restaurant_lon = lon + random.uniform(-0.005, 0.005)
                
                # 툴팁 내용 생성 (마우스 오버 시 표시될 정보)
                tooltip_content = f"""
                <b>{restaurant.get('name', 'Unknown')}</b><br>
                평점: {restaurant.get('rating', 'N/A')}<br>
                리뷰 수: {restaurant.get('reviews', 'N/A')}<br>
                가격대: {restaurant.get('price_range', 'N/A')}<br>
                """

                # 팝업 내용 생성 (클릭 시 표시될 상세 정보)
                popup_content = f"""
                <b>{restaurant.get('name', 'Unknown')}</b><br>
                평점: {restaurant.get('rating', 'N/A')}<br>
                리뷰 수: {restaurant.get('reviews', 'N/A')}<br>
                리뷰 요약: {restaurant.get('review_summary', 'N/A')}<br>
                주소: {restaurant.get('address', 'N/A')}<br>
                전화번호: {restaurant.get('phone', 'N/A')}<br>
                영업시간: {restaurant.get('hours', 'N/A')}<br>
                가격대: {restaurant.get('price_range', 'N/A')}<br>
                추천 이유: {restaurant.get('reason', 'N/A')}
                """

                # 지도에 맛집 위치 표시
                folium.Marker(
                    [restaurant_lat, restaurant_lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=folium.Tooltip(tooltip_content),
                    icon=folium.Icon(color='green', icon='cutlery', prefix='fa')
                ).add_to(m)

        else:
            st.error("예상치 못한 응답 형식입니다. 다시 시도해 주세요.")
    except Exception as e:
        st.error(f"오류 발생: {str(e)}")

    # 지도 표시
    st.subheader(f"{location}의 {menu} 맛집 지도")
    folium_static(m, width=700, height=500)

# 앱 설명
st.sidebar.markdown("---")
st.sidebar.info("이 앱은 도쿄의 맛집을 추천해주는 서비스입니다. "
                 "원하는 지역과 메뉴를 선택한 후 'OpenAI GPT' 또는 'Google Gemini' API를 선택하여 "
                 "맛집 추천을 받아보세요.")