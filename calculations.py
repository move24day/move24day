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
                            print(f"Error: Item '{item_name}' not found in data.items.")
                        except Exception as e:
                            print(f"Error processing item '{item_name}': {e}")
                    processed_items.add(item_name)
    return round(total_volume, 2), round(total_weight, 2)

# --- 차량 추천 (current_move_type 인자 받는 수정된 버전) ---
def recommend_vehicle(total_volume, total_weight, current_move_type):
    recommended_vehicle = None
    remaining_space_percent = 0.0

    if not hasattr(data, 'vehicle_specs') or not data.vehicle_specs:
        # print("DEBUG CALC: No vehicle_specs found in data.py")
        return None, 0

    priced_trucks_for_move_type = []
    if hasattr(data, 'vehicle_prices') and current_move_type in data.vehicle_prices:
        priced_trucks_for_move_type = list(data.vehicle_prices[current_move_type].keys())

    if not priced_trucks_for_move_type:
        # print(f"DEBUG CALC: No priced trucks for move type '{current_move_type}'.")
        return None, 0

    relevant_vehicle_specs = {
        truck: specs for truck, specs in data.vehicle_specs.items() if truck in priced_trucks_for_move_type
    }

    if not relevant_vehicle_specs:
        # print(f"DEBUG CALC: No relevant_vehicle_specs for move type '{current_move_type}'.")
        return None, 0

    sorted_trucks = sorted(relevant_vehicle_specs.items(), key=lambda item: item[1].get('capacity', 0))

    if total_volume <= 0 and total_weight <= 0:
        # print("DEBUG CALC: Zero volume and weight, no recommendation.")
        return None, 0

    loading_efficiency = getattr(data, 'LOADING_EFFICIENCY', 1.0)

    for truck_name, specs in sorted_trucks:
        usable_capacity = specs.get('capacity', 0) * loading_efficiency
        usable_weight = specs.get('weight_capacity', 0)

        if usable_capacity > 0:
            if total_volume <= usable_capacity and total_weight <= usable_weight:
                recommended_vehicle = truck_name
                remaining_space_percent = (1 - (total_volume / usable_capacity)) * 100 if usable_capacity > 0 else 0
                # print(f"DEBUG CALC: Recommended '{recommended_vehicle}' for V:{total_volume}, W:{total_weight}")
                break
    
    if recommended_vehicle:
        return recommended_vehicle, round(remaining_space_percent, 1)
    elif (total_volume > 0 or total_weight > 0) and sorted_trucks:
        # print(f"DEBUG CALC: Volume/Weight ({total_volume}/{total_weight}) exceeds largest available truck '{sorted_trucks[-1][0]}'.")
        return f"{sorted_trucks[-1][0]} 용량 초과", 0
    else:
        # print(f"DEBUG CALC: No suitable vehicle found for V:{total_volume}, W:{total_weight}")
        return None, 0


# --- 층수 숫자 추출 ---
def get_floor_num(floor_str):
    try:
        if floor_str is None: return 0
        cleaned_floor_str = str(floor_str).strip()
        if not cleaned_floor_str: return 0
        if cleaned_floor_str.startswith('-'):
            numeric_part = ''.join(filter(str.isdigit, cleaned_floor_str[1:]))
            return -int(numeric_part) if numeric_part else 0
        else:
            numeric_part = ''.join(filter(str.isdigit, cleaned_floor_str))
            return int(numeric_part) if numeric_part else 0
    except (ValueError, TypeError): return 0

# --- 사다리차 비용 계산 ---
def get_ladder_cost(floor_num, vehicle_name):
    cost = 0
    note = ""
    if floor_num < 2: return 0, "1층 이하"
    floor_range_key = None
    if hasattr(data, 'ladder_price_floor_ranges'):
        for (min_f, max_f), range_str in data.ladder_price_floor_ranges.items():
            if min_f <= floor_num <= max_f:
                floor_range_key = range_str
                break
    if not floor_range_key: return 0, f"{floor_num}층 해당 가격 없음"

    vehicle_spec = getattr(data, 'vehicle_specs', {}).get(vehicle_name)
    if not vehicle_spec or 'weight_capacity' not in vehicle_spec: return 0, "선택 차량 정보 없음"
    
    vehicle_tonnage_num = vehicle_spec['weight_capacity'] / 1000.0
    tonnage_key = None
    if hasattr(data, 'ladder_tonnage_map'):
        for ton_num in sorted(data.ladder_tonnage_map.keys(), reverse=True):
             if vehicle_tonnage_num >= ton_num:
                 tonnage_key = data.ladder_tonnage_map[ton_num]
                 break
    if not tonnage_key: tonnage_key = getattr(data, 'default_ladder_size', None)
    if not tonnage_key: return 0, "사다리차 톤수 기준 없음"

    try:
        if not hasattr(data, 'ladder_prices'): return 0, "사다리차 가격표 없음"
        floor_prices = data.ladder_prices.get(floor_range_key, {})
        cost = floor_prices.get(tonnage_key, 0)
        if cost > 0:
            note = f"{floor_range_key}, {tonnage_key} 기준"
        else:
            default_size = getattr(data, 'default_ladder_size', None)
            if default_size and default_size != tonnage_key:
                 cost = floor_prices.get(default_size, 0)
                 note = f"{floor_range_key}, 기본({default_size}) 기준 적용" if cost > 0 else f"{floor_range_key}, {tonnage_key}(기본 {default_size}) 가격 정보 없음"
            else:
                 note = f"{floor_range_key}, {tonnage_key} 가격 정보 없음"
    except Exception as e:
        note = f"가격 조회 중 오류: {e}"; cost = 0
    return cost, note

# --- 총 이사 비용 계산 ---
def calculate_total_moving_cost(state_data):
    total_cost = 0
    cost_items = []
    personnel_info = {}

    current_move_type = state_data.get('base_move_type')
    selected_vehicle = state_data.get('final_selected_vehicle')
    is_storage = state_data.get('is_storage_move', False)
    has_via_point = state_data.get('has_via_point', False)

    if not selected_vehicle:
        cost_items.append(("오류", 0, "차량을 선택해야 비용 계산 가능"))
        return 0, cost_items, {}

    base_price, base_men, base_women = 0, 0, 0
    vehicle_prices_options = getattr(data, 'vehicle_prices', {}).get(current_move_type, {})
    if selected_vehicle in vehicle_prices_options:
        vehicle_info = vehicle_prices_options[selected_vehicle]
        base_price = vehicle_info.get('price', 0)
        base_men = vehicle_info.get('men', 0)
        base_women = vehicle_info.get('housewife', 0)
        actual_base_price = base_price * 2 if is_storage else base_price
        base_note = f"{selected_vehicle} 기준" + (" (보관이사 운임 x2)" if is_storage else "")
        cost_items.append(("기본 운임", actual_base_price, base_note))
        total_cost += actual_base_price
    else:
        cost_items.append(("오류", 0, f"선택된 차량({selected_vehicle}) 가격 정보 없음"))
        return 0, cost_items, {}

    from_floor_num = get_floor_num(state_data.get('from_floor'))
    to_floor_num = get_floor_num(state_data.get('to_floor'))
    from_method = state_data.get('from_method')
    to_method = state_data.get('to_method')

    if from_method == "사다리차 🪜":
        ladder_cost, ladder_note = get_ladder_cost(from_floor_num, selected_vehicle)
        if ladder_cost > 0 or (ladder_cost == 0 and ladder_note != "1층 이하"):
            cost_items.append(("출발지 사다리차", ladder_cost, ladder_note))
            total_cost += ladder_cost
    if to_method == "사다리차 🪜":
        ladder_cost, ladder_note = get_ladder_cost(to_floor_num, selected_vehicle)
        if ladder_cost > 0 or (ladder_cost == 0 and ladder_note != "1층 이하"):
            cost_items.append(("도착지 사다리차", ladder_cost, ladder_note))
            total_cost += ladder_cost

    sky_hours_from = max(1, int(state_data.get('sky_hours_from', 1) or 1))
    sky_hours_final = max(1, int(state_data.get('sky_hours_final', 1) or 1))

    if from_method == "스카이 🏗️":
        cost_from_sky = data.SKY_BASE_PRICE + data.SKY_EXTRA_HOUR_PRICE * (sky_hours_from - 1)
        note_from_sky = f"출발({sky_hours_from}시간): 기본 {data.SKY_BASE_PRICE:,.0f}원" + (f" + 추가 {data.SKY_EXTRA_HOUR_PRICE*(sky_hours_from-1):,.0f}원" if sky_hours_from > 1 else "")
        cost_items.append(("출발지 스카이 장비", cost_from_sky, note_from_sky))
        total_cost += cost_from_sky
    if to_method == "스카이 🏗️":
        cost_to_sky = data.SKY_BASE_PRICE + data.SKY_EXTRA_HOUR_PRICE * (sky_hours_final - 1)
        note_to_sky = f"도착({sky_hours_final}시간): 기본 {data.SKY_BASE_PRICE:,.0f}원" + (f" + 추가 {data.SKY_EXTRA_HOUR_PRICE*(sky_hours_final-1):,.0f}원" if sky_hours_final > 1 else "")
        cost_items.append(("도착지 스카이 장비", cost_to_sky, note_to_sky))
        total_cost += cost_to_sky
    
    add_men = int(state_data.get('add_men', 0) or 0)
    add_women = int(state_data.get('add_women', 0) or 0)
    manual_added_cost = (add_men + add_women) * data.ADDITIONAL_PERSON_COST
    if manual_added_cost > 0:
        cost_items.append(("추가 인력", manual_added_cost, f"남{add_men}, 여{add_women}"))
        total_cost += manual_added_cost

    actual_remove_housewife = False
    if state_data.get('remove_base_housewife', False) and base_women > 0:
        discount = -data.ADDITIONAL_PERSON_COST * base_women
        cost_items.append(("기본 여성 인원 제외 할인", discount, f"여 {base_women}명 제외"))
        total_cost += discount
        actual_remove_housewife = True

    adjustment_amount = int(state_data.get('adjustment_amount', 0) or 0)
    if adjustment_amount != 0:
        adj_label = "할증 조정" if adjustment_amount > 0 else "할인 조정"
        cost_items.append((f"{adj_label} 금액", adjustment_amount, "수동 입력"))
        total_cost += adjustment_amount

    if is_storage:
        duration = max(1, int(state_data.get('storage_duration', 1) or 1))
        storage_type = state_data.get('storage_type', data.DEFAULT_STORAGE_TYPE)
        daily_rate = data.STORAGE_RATES_PER_DAY.get(storage_type, 0)
        if daily_rate > 0:
            base_storage_cost = daily_rate * duration
            electricity_surcharge = 0
            storage_note = f"{storage_type}, {duration}일"
            if state_data.get('storage_use_electricity', False):
                electricity_surcharge_per_day = getattr(data, 'STORAGE_ELECTRICITY_SURCHARGE_PER_DAY', 3000)
                electricity_surcharge = electricity_surcharge_per_day * duration
                storage_note += ", 전기사용"
            final_storage_cost = base_storage_cost + electricity_surcharge
            cost_items.append(("보관료", final_storage_cost, storage_note))
            total_cost += final_storage_cost
        else:
            cost_items.append(("오류", 0, f"보관 유형({storage_type}) 요금 정보 없음"))

    if state_data.get('apply_long_distance', False):
        selector = state_data.get('long_distance_selector')
        if selector and selector != "선택 안 함":
            cost = data.long_distance_prices.get(selector, 0)
            if cost > 0:
                cost_items.append(("장거리 운송료", cost, selector))
                total_cost += cost
    
    if state_data.get('has_waste_check', False):
        tons = max(0.5, float(state_data.get('waste_tons_input', 0.5) or 0.5))
        cost = data.WASTE_DISPOSAL_COST_PER_TON * tons
        cost_items.append(("폐기물 처리", cost, f"{tons:.1f}톤 기준"))
        total_cost += cost

    date_surcharge = 0
    date_notes = []
    date_opts = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
    for i, option in enumerate(date_opts):
        if state_data.get(f"date_opt_{i}_widget", False): # Key from ui_tab3
            surcharge = data.special_day_prices.get(option, 0)
            if surcharge > 0:
                date_surcharge += surcharge
                date_notes.append(option.split(" ")[0])
    if date_surcharge > 0:
        cost_items.append(("날짜 할증", date_surcharge, ", ".join(date_notes)))
        total_cost += date_surcharge

    regional_ladder_surcharge = int(state_data.get('regional_ladder_surcharge', 0) or 0)
    if regional_ladder_surcharge > 0:
        cost_items.append(("지방 사다리 추가요금", regional_ladder_surcharge, "수동 입력"))
        total_cost += regional_ladder_surcharge

    if has_via_point:
        via_surcharge = int(state_data.get('via_point_surcharge', 0) or 0)
        if via_surcharge > 0:
            cost_items.append(("경유지 추가요금", via_surcharge, "수동 입력"))
            total_cost += via_surcharge

    final_men = base_men + add_men
    final_women = (base_women + add_women) if not actual_remove_housewife else add_women
    personnel_info = {
        'base_men': base_men, 'base_women': base_women,
        'manual_added_men': add_men, 'manual_added_women': add_women,
        'final_men': final_men, 'final_women': final_women
    }
    return max(0, round(total_cost)), cost_items, personnel_info