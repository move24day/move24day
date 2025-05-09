# calculations.py

import data
import math

# --- 이사짐 부피/무게 계산 ---
def calculate_total_volume_weight(state_data, move_type):
    total_volume = 0.0
    total_weight = 0.0
    item_defs = data.item_definitions.get(move_type, {})
    processed_items = set()
    if isinstance(item_defs, dict):
        for section, item_list in item_defs.items():
            if section == "폐기 처리 품목 🗑️":
                continue
            if isinstance(item_list, list):
                for item_name in item_list:
                    if item_name in processed_items or item_name not in data.items:
                        continue
                    widget_key = f"qty_{move_type}_{section}_{item_name}"
                    qty_raw = state_data.get(widget_key)
                    qty = 0
                    try:
                        qty = int(qty_raw) if qty_raw is not None else 0
                    except (ValueError, TypeError):
                        qty = 0

                    if qty > 0:
                        try:
                            volume, weight = data.items[item_name]
                            total_volume += volume * qty
                            total_weight += weight * qty
                        except KeyError:
                            print(f"Error: Item '{item_name}' not found.")
                        except Exception as e:
                            print(f"Error processing item '{item_name}': {e}")
                    processed_items.add(item_name)
    return round(total_volume, 2), round(total_weight, 2)

# --- 차량 추천 (수정됨) ---
def recommend_vehicle(total_volume, total_weight, current_move_type): # current_move_type 인자 추가
    recommended_vehicle = None
    remaining_space_percent = 0.0

    if not hasattr(data, 'vehicle_specs') or not data.vehicle_specs:
        return None, 0

    # 현재 이사 유형에 대해 가격이 책정된 차량 목록 가져오기
    priced_trucks_for_move_type = []
    if hasattr(data, 'vehicle_prices') and current_move_type in data.vehicle_prices:
        priced_trucks_for_move_type = list(data.vehicle_prices[current_move_type].keys())

    if not priced_trucks_for_move_type: # 이 이사 유형에 가격 책정된 차량이 없으면 추천 불가
        print(f"Warning: No priced trucks found for move type '{current_move_type}' in data.vehicle_prices.")
        return None, 0

    # vehicle_specs에서 가격 책정된 차량들만 필터링하고 용량순으로 정렬
    relevant_vehicle_specs = {
        truck: specs for truck, specs in data.vehicle_specs.items() if truck in priced_trucks_for_move_type
    }

    if not relevant_vehicle_specs: # 가격 책정된 차량에 대한 스펙 정보가 없으면 추천 불가
        print(f"Warning: No vehicle_specs found for priced trucks of move type '{current_move_type}'.")
        return None, 0

    sorted_trucks = sorted(relevant_vehicle_specs.items(), key=lambda item: item[1].get('capacity', 0))

    if total_volume <= 0 and total_weight <= 0:
        return None, 0 # 물품이 없으면 추천 없음

    loading_efficiency = getattr(data, 'LOADING_EFFICIENCY', 1.0)

    for truck_name, specs in sorted_trucks: # 가격이 책정된 차량들 중에서만 추천
        usable_capacity = specs.get('capacity', 0) * loading_efficiency
        usable_weight = specs.get('weight_capacity', 0)

        if usable_capacity > 0: # 무게 용량은 0일 수도 있으나, 부피 용량은 0보다 커야 함
            if total_volume <= usable_capacity and total_weight <= usable_weight:
                recommended_vehicle = truck_name
                remaining_space_percent = (1 - (total_volume / usable_capacity)) * 100 if usable_capacity > 0 else 0
                break
    
    if recommended_vehicle:
        return recommended_vehicle, round(remaining_space_percent, 1)
    elif (total_volume > 0 or total_weight > 0) and sorted_trucks: # sorted_trucks는 이제 필터링된 리스트
        # 필터링된 차량 중 가장 큰 차량의 용량도 초과한 경우
        return f"{sorted_trucks[-1][0]} 용량 초과", 0
    else:
        # 추천 가능한 차량이 없는 다른 경우 (예: 모든 관련 차량이 너무 작음 - 이 경우는 위에서 처리됨)
        # 또는 물량은 있지만 정렬된 트럭이 없는 극단적 경우 (relevant_vehicle_specs가 비어있으면 위에서 처리됨)
        return None, 0


# --- 층수 숫자 추출 (수정된 함수) ---
def get_floor_num(floor_str):
    """문자열 형태의 층수 입력을 정수형으로 변환합니다. 지하, 공백 등을 처리합니다."""
    try:
        if floor_str is None:
            return 0
        cleaned_floor_str = str(floor_str).strip()
        if not cleaned_floor_str:
            return 0

        if cleaned_floor_str.startswith('-'):
            numeric_part = ''.join(filter(str.isdigit, cleaned_floor_str[1:]))
            return -int(numeric_part) if numeric_part else 0
        else:
            numeric_part = ''.join(filter(str.isdigit, cleaned_floor_str))
            return int(numeric_part) if numeric_part else 0
    except (ValueError, TypeError):
        return 0

# --- 사다리차 비용 계산 ---
def get_ladder_cost(floor_num, vehicle_name):
    cost = 0
    note = ""

    if floor_num < 2:
        return 0, "1층 이하"

    floor_range_key = None
    ladder_ranges = getattr(data, 'ladder_price_floor_ranges', None)
    if ladder_ranges and isinstance(ladder_ranges, dict):
        for (min_f, max_f), range_str in ladder_ranges.items():
            if min_f <= floor_num <= max_f:
                floor_range_key = range_str
                break

    if not floor_range_key:
        return 0, f"{floor_num}층 해당 가격 없음"

    vehicle_specs = getattr(data, 'vehicle_specs', None)
    vehicle_spec = vehicle_specs.get(vehicle_name) if vehicle_specs else None
    if not vehicle_spec or 'weight_capacity' not in vehicle_spec:
        return 0, "선택 차량 정보 없음"

    vehicle_tonnage_num = vehicle_spec['weight_capacity'] / 1000.0
    tonnage_key = None
    ladder_tonnage_map = getattr(data, 'ladder_tonnage_map', None)
    if ladder_tonnage_map and isinstance(ladder_tonnage_map, dict):
        sorted_tonnage_keys = sorted(ladder_tonnage_map.keys(), reverse=True)
        for ton_num in sorted_tonnage_keys:
             if vehicle_tonnage_num >= ton_num:
                 tonnage_key = ladder_tonnage_map[ton_num]
                 break

    if not tonnage_key:
        tonnage_key = getattr(data, 'default_ladder_size', None)

    if not tonnage_key:
        return 0, "사다리차 톤수 기준 없음"

    try:
        ladder_prices = getattr(data, 'ladder_prices', None)
        if not ladder_prices or not isinstance(ladder_prices, dict):
            return 0, "사다리차 가격표 없음"

        floor_prices = ladder_prices.get(floor_range_key, {})
        cost = floor_prices.get(tonnage_key, 0)

        if cost > 0:
            note = f"{floor_range_key}, {tonnage_key} 기준"
        else:
            default_size = getattr(data, 'default_ladder_size', None)
            if default_size and default_size != tonnage_key:
                 cost = floor_prices.get(default_size, 0)
                 if cost > 0:
                     note = f"{floor_range_key}, 기본({default_size}) 기준 적용"
                 else:
                     note = f"{floor_range_key}, {tonnage_key}(기본 {default_size}) 가격 정보 없음"
            else:
                 note = f"{floor_range_key}, {tonnage_key} 가격 정보 없음"
    except Exception as e:
        note = f"가격 조회 중 오류: {e}"
        cost = 0

    return cost, note

# --- 총 이사 비용 계산 (보관료 전기요금 추가) ---
def calculate_total_moving_cost(state_data):
    total_cost = 0
    cost_items = []
    personnel_info = {}

    current_move_type = state_data.get('base_move_type')
    selected_vehicle = state_data.get('final_selected_vehicle')
    is_storage = state_data.get('is_storage_move', False)
    has_via_point = state_data.get('has_via_point', False)

    # print("-" * 30)
    # print(f"DEBUG: Starting cost calculation for vehicle: {selected_vehicle}")

    if not selected_vehicle:
        cost_items.append(("오류", 0, "차량을 선택해야 비용 계산 가능"))
        return 0, cost_items, {}

    base_price = 0
    base_men = 0
    base_women = 0

    vehicle_prices_options = data.vehicle_prices.get(current_move_type, {})
    if selected_vehicle in vehicle_prices_options:
        vehicle_info = vehicle_prices_options[selected_vehicle]
        base_price = vehicle_info.get('price', 0)
        base_men = vehicle_info.get('men', 0)
        base_women = vehicle_info.get('housewife', 0)

        if is_storage:
            calculated_base_price = base_price * 2
            base_note = f"{selected_vehicle} 기준 (보관이사 운임 x2)"
            cost_items.append(("기본 운임", calculated_base_price, base_note))
            total_cost += calculated_base_price
        else:
            cost_items.append(("기본 운임", base_price, f"{selected_vehicle} 기준"))
            total_cost += base_price
    else:
        cost_items.append(("오류", 0, f"선택된 차량({selected_vehicle}) 가격 정보 없음"))
        return 0, cost_items, {}

    # print(f"DEBUG: Base cost calculated: {total_cost}")

    from_floor_num = get_floor_num(state_data.get('from_floor'))
    to_floor_num = get_floor_num(state_data.get('to_floor'))
    from_method = state_data.get('from_method')
    to_method = state_data.get('to_method')

    if from_method == "사다리차 🪜":
        ladder_cost, ladder_note = get_ladder_cost(from_floor_num, selected_vehicle)
        if ladder_cost > 0:
            cost_items.append(("출발지 사다리차", ladder_cost, ladder_note))
            total_cost += ladder_cost
        elif ladder_note != "1층 이하": 
            cost_items.append(("출발지 사다리차", 0, ladder_note))


    if to_method == "사다리차 🪜":
        ladder_cost, ladder_note = get_ladder_cost(to_floor_num, selected_vehicle)
        if ladder_cost > 0:
            cost_items.append(("도착지 사다리차", ladder_cost, ladder_note))
            total_cost += ladder_cost
        elif ladder_note != "1층 이하": 
            cost_items.append(("도착지 사다리차", 0, ladder_note))


    sky_hours_from_raw = state_data.get('sky_hours_from', 1)
    sky_hours_final_raw = state_data.get('sky_hours_final', 1)
    try: sky_hours_from = max(1, int(sky_hours_from_raw))
    except (ValueError, TypeError): sky_hours_from = 1
    try: sky_hours_final = max(1, int(sky_hours_final_raw))
    except (ValueError, TypeError): sky_hours_final = 1


    if from_method == "스카이 🏗️":
        cost_from_sky = data.SKY_BASE_PRICE + data.SKY_EXTRA_HOUR_PRICE * (sky_hours_from - 1)
        note_from_sky = f"출발({sky_hours_from}시간): 기본 {data.SKY_BASE_PRICE:,.0f}원"
        if sky_hours_from > 1:
            note_from_sky += f" + 추가 {data.SKY_EXTRA_HOUR_PRICE*(sky_hours_from-1):,.0f}원"
        cost_items.append(("출발지 스카이 장비", cost_from_sky, note_from_sky))
        total_cost += cost_from_sky

    if to_method == "스카이 🏗️":
        cost_to_sky = data.SKY_BASE_PRICE + data.SKY_EXTRA_HOUR_PRICE * (sky_hours_final - 1)
        note_to_sky = f"도착({sky_hours_final}시간): 기본 {data.SKY_BASE_PRICE:,.0f}원"
        if sky_hours_final > 1:
            note_to_sky += f" + 추가 {data.SKY_EXTRA_HOUR_PRICE*(sky_hours_final-1):,.0f}원"
        cost_items.append(("도착지 스카이 장비", cost_to_sky, note_to_sky))
        total_cost += cost_to_sky

    add_men_raw = state_data.get('add_men', 0)
    add_women_raw = state_data.get('add_women', 0)
    try: add_men = int(add_men_raw) if add_men_raw is not None else 0
    except (ValueError, TypeError): add_men = 0
    try: add_women = int(add_women_raw) if add_women_raw is not None else 0
    except (ValueError, TypeError): add_women = 0


    manual_added_cost = (add_men + add_women) * data.ADDITIONAL_PERSON_COST
    if manual_added_cost > 0:
        cost_items.append(("추가 인력", manual_added_cost, f"남{add_men}, 여{add_women}"))
        total_cost += manual_added_cost

    auto_added_men = 0 

    remove_base_housewife = state_data.get('remove_base_housewife', False)
    actual_remove_housewife = False
    if remove_base_housewife and base_women > 0:
        discount = -data.ADDITIONAL_PERSON_COST * base_women
        cost_items.append(("기본 여성 인원 제외 할인", discount, f"여 {base_women}명 제외"))
        total_cost += discount
        actual_remove_housewife = True

    adjustment_amount_raw = state_data.get('adjustment_amount', 0)
    try:
        adjustment_amount = int(adjustment_amount_raw)
    except (ValueError, TypeError):
        adjustment_amount = 0
    
    if adjustment_amount != 0:
        adj_label = "할증 조정" if adjustment_amount > 0 else "할인 조정"
        cost_items.append((f"{adj_label} 금액", adjustment_amount, "수동 입력")) 
        total_cost += adjustment_amount


    if is_storage:
        duration_raw = state_data.get('storage_duration', 1)
        try: duration = max(1, int(duration_raw))
        except (ValueError, TypeError): duration = 1

        selected_storage_type = state_data.get('storage_type', data.DEFAULT_STORAGE_TYPE)
        daily_rate = data.STORAGE_RATES_PER_DAY.get(selected_storage_type, data.STORAGE_RATES_PER_DAY.get(data.DEFAULT_STORAGE_TYPE, 0))

        if daily_rate > 0:
            base_storage_cost = daily_rate * duration
            use_electricity = state_data.get('storage_use_electricity', False)
            electricity_surcharge = 0
            storage_note = f"{selected_storage_type}, {duration}일"

            if use_electricity:
                electricity_surcharge_per_day = getattr(data, 'STORAGE_ELECTRICITY_SURCHARGE_PER_DAY', 3000) 
                electricity_surcharge = electricity_surcharge_per_day * duration
                storage_note += ", 전기사용"

            final_storage_cost = base_storage_cost + electricity_surcharge
            cost_items.append(("보관료", final_storage_cost, storage_note))
            total_cost += final_storage_cost
        else:
            cost_items.append(("오류", 0, f"보관 유형({selected_storage_type}) 요금 정보 없음"))

    apply_long = state_data.get('apply_long_distance', False)
    selector = state_data.get('long_distance_selector')
    if apply_long and selector and selector != "선택 안 함":
        cost = data.long_distance_prices.get(selector, 0)
        if cost > 0:
            cost_items.append(("장거리 운송료", cost, selector))
            total_cost += cost

    has_waste = state_data.get('has_waste_check', False)
    tons_raw = state_data.get('waste_tons_input', 0.5)
    try:
        tons = float(tons_raw) if tons_raw is not None else 0.5
        tons = max(0.5, tons) 
    except (ValueError, TypeError): tons = 0.5


    if has_waste:
        cost = data.WASTE_DISPOSAL_COST_PER_TON * tons
        cost_items.append(("폐기물 처리", cost, f"{tons:.1f}톤 기준")) 
        total_cost += cost

    date_surcharge = 0
    date_notes = []
    date_opts = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
    for i, option in enumerate(date_opts):
        if state_data.get(f"date_opt_{i}_widget", False):
            surcharge = data.special_day_prices.get(option, 0)
            if surcharge > 0:
                date_surcharge += surcharge
                simple_option_name = option.split(" ")[0]
                date_notes.append(simple_option_name)
    if date_surcharge > 0:
        cost_items.append(("날짜 할증", date_surcharge, ", ".join(date_notes)))
        total_cost += date_surcharge

    regional_ladder_surcharge_raw = state_data.get('regional_ladder_surcharge', 0)
    try: regional_ladder_surcharge = int(regional_ladder_surcharge_raw)
    except (ValueError, TypeError): regional_ladder_surcharge = 0
    if regional_ladder_surcharge > 0:
        cost_items.append(("지방 사다리 추가요금", regional_ladder_surcharge, "수동 입력"))
        total_cost += regional_ladder_surcharge

    if has_via_point:
        via_surcharge_raw = state_data.get('via_point_surcharge', 0)
        try:
            via_surcharge = int(via_surcharge_raw)
            if via_surcharge > 0:
                cost_items.append(("경유지 추가요금", via_surcharge, "수동 입력"))
                total_cost += via_surcharge
        except (ValueError, TypeError):
            print(f"DEBUG: via_point_surcharge conversion failed for value: {via_surcharge_raw}")


    final_men = base_men + add_men + auto_added_men
    final_women = (base_women + add_women) if not actual_remove_housewife else add_women

    personnel_info = {
        'base_men': base_men, 'base_women': base_women,
        'manual_added_men': add_men, 'manual_added_women': add_women,
        'auto_added_men': auto_added_men, 
        'remove_base_housewife': actual_remove_housewife,
        'final_men': final_men, 'final_women': final_women
    }

    # print(f"DEBUG: total_cost *before* max(0, total_cost): {total_cost}")
    final_total_cost = max(0, round(total_cost)) 
    # print(f"DEBUG: final_total_cost *after* max(0, round(total_cost)): {final_total_cost}")
    # print("-" * 30)

    return final_total_cost, cost_items, personnel_info
