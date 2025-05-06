# calculations.py (Read prefixed key for regional surcharge)
import data
import math

# --- 이사짐 부피/무게 계산 ---
def calculate_total_volume_weight(state_data, move_type):
    total_volume = 0.0; total_weight = 0.0; item_defs = data.item_definitions.get(move_type, {}); processed_items = set()
    if isinstance(item_defs, dict):
        for section, item_list in item_defs.items():
            if section == "폐기 처리 품목 🗑️": continue
            if isinstance(item_list, list):
                for item_name in item_list:
                    if item_name in processed_items or item_name not in data.items: continue
                    # Correct key format for items based on move_type argument
                    widget_key = f"qty_{move_type}_{section}_{item_name}"

                    qty_raw = state_data.get(widget_key); qty = 0
                    try: qty = int(qty_raw) if qty_raw is not None else 0
                    except (ValueError, TypeError): qty = 0
                    if qty > 0:
                        try: volume, weight = data.items[item_name]; total_volume += volume * qty; total_weight += weight * qty
                        except KeyError: print(f"Error: Item '{item_name}' not found in data.items.")
                        except Exception as e: print(f"Error processing item '{item_name}': {e}")
                    processed_items.add(item_name)
    return round(total_volume, 2), round(total_weight, 2)


# --- 차량 추천 ---
def recommend_vehicle(total_volume, total_weight):
    recommended_vehicle = None; remaining_space_percent = 0.0;
    if not hasattr(data, 'vehicle_specs') or not data.vehicle_specs: return None, 0
    sorted_trucks = sorted(data.vehicle_specs.items(), key=lambda item: item[1].get('capacity', 0));
    if total_volume <= 0 and total_weight <= 0: return None, 0
    loading_efficiency = getattr(data, 'LOADING_EFFICIENCY', 1.0)
    for truck_name, specs in sorted_trucks:
        usable_capacity = specs.get('capacity', 0) * loading_efficiency; usable_weight = specs.get('weight_capacity', 0)
        if usable_capacity > 0 and usable_weight >= 0:
            if total_volume <= usable_capacity and total_weight <= usable_weight:
                recommended_vehicle = truck_name
                remaining_space_percent = (1 - (total_volume / usable_capacity)) * 100 if usable_capacity > 0 else 0; break
    if recommended_vehicle: return recommended_vehicle, round(remaining_space_percent, 1)
    elif (total_volume > 0 or total_weight > 0) and sorted_trucks: return f"{sorted_trucks[-1][0]} 용량 초과", 0
    else: return None, 0


# --- 층수 숫자 추출 ---
def get_floor_num(floor_str):
    try:
        if floor_str is None: return 0
        cleaned_floor_str = str(floor_str).strip().upper();
        if not cleaned_floor_str: return 0
        if cleaned_floor_str.startswith('B'): numeric_part = ''.join(filter(str.isdigit, cleaned_floor_str[1:])); return -int(numeric_part) if numeric_part else 0
        elif cleaned_floor_str.startswith('-'): numeric_part = ''.join(filter(str.isdigit, cleaned_floor_str[1:])); return -int(numeric_part) if numeric_part else 0
        else: numeric_part = ''.join(filter(str.isdigit, cleaned_floor_str)); return int(numeric_part) if numeric_part else 0
    except (ValueError, TypeError): return 0

# --- 사다리차 비용 계산 ---
def get_ladder_cost(floor_num, vehicle_name):
    cost = 0; note = "";
    if floor_num < 2: return 0, "1층 이하"
    floor_range_key = None; ladder_ranges = getattr(data, 'ladder_price_floor_ranges', None)
    if ladder_ranges and isinstance(ladder_ranges, dict):
        for (min_f, max_f), range_str in sorted(ladder_ranges.items()):
            if min_f <= floor_num <= max_f: floor_range_key = range_str; break
    if not floor_range_key: return 0, f"{floor_num}층 해당 가격 없음"
    vehicle_specs = getattr(data, 'vehicle_specs', None); vehicle_spec = vehicle_specs.get(vehicle_name) if vehicle_specs else None
    if not vehicle_spec or 'weight_capacity' not in vehicle_spec: return 0, "선택 차량 정보 없음"
    vehicle_tonnage_num = vehicle_spec['weight_capacity'] / 1000.0; tonnage_key = None
    ladder_tonnage_map = getattr(data, 'ladder_tonnage_map', None)
    if ladder_tonnage_map and isinstance(ladder_tonnage_map, dict):
        sorted_tonnage_keys = sorted(ladder_tonnage_map.keys(), reverse=True)
        for ton_num in sorted_tonnage_keys:
             if vehicle_tonnage_num >= ton_num: tonnage_key = ladder_tonnage_map[ton_num]; break
    if not tonnage_key: tonnage_key = getattr(data, 'default_ladder_size', None)
    if not tonnage_key: return 0, "사다리차 톤수 기준 없음"
    try:
        ladder_prices = getattr(data, 'ladder_prices', None)
        if not ladder_prices or not isinstance(ladder_prices, dict): return 0, "사다리차 가격표 없음"
        floor_prices = ladder_prices.get(floor_range_key, {}); cost = floor_prices.get(tonnage_key, 0)
        if cost > 0: note = f"{floor_range_key}, {tonnage_key} 기준"
        else:
            default_size = getattr(data, 'default_ladder_size', None)
            if default_size and default_size != tonnage_key:
                 cost = floor_prices.get(default_size, 0)
                 if cost > 0: note = f"{floor_range_key}, 기본({default_size}) 기준 적용"
                 else: note = f"{floor_range_key}, {tonnage_key}(기본 {default_size}) 가격 정보 없음"
            else: note = f"{floor_range_key}, {tonnage_key} 가격 정보 없음"
    except Exception as e: note = f"가격 조회 중 오류: {e}"; cost = 0
    return cost, note


# --- 총 이사 비용 계산 (*** 변경된 키 읽기 적용 ***) ---
def calculate_total_moving_cost(state_data):
    total_cost = 0; cost_items = []; personnel_info = {}; current_move_type = state_data.get('base_move_type'); selected_vehicle = state_data.get('final_selected_vehicle'); is_storage = state_data.get('is_storage_move', False)
    print("-" * 30); print(f"DEBUG: Starting cost calculation for vehicle: {selected_vehicle}")

    if not selected_vehicle: cost_items.append(("오류", 0, "차량을 선택해야 비용 계산 가능")); return 0, cost_items, {}
    base_price = 0; base_men = 0; base_women = 0; vehicle_prices_options = data.vehicle_prices.get(current_move_type, {})
    if selected_vehicle in vehicle_prices_options:
        vehicle_info = vehicle_prices_options[selected_vehicle]; base_price = vehicle_info.get('price', 0); base_men = vehicle_info.get('men', 0); base_women = vehicle_info.get('housewife', 0)
        if is_storage: calculated_base_price = base_price * 2; base_note = f"{selected_vehicle} 기준 (보관이사 운임 x2)"; cost_items.append(("기본 운임", calculated_base_price, base_note)); total_cost += calculated_base_price
        else: cost_items.append(("기본 운임", base_price, f"{selected_vehicle} 기준")); total_cost += base_price
    else: cost_items.append(("오류", 0, f"선택된 차량({selected_vehicle}) 가격 정보 없음")); return 0, cost_items, {}
    print(f"DEBUG: Base cost calculated: {total_cost}")

    from_floor_num = get_floor_num(state_data.get('from_floor')); to_floor_num = get_floor_num(state_data.get('to_floor')); from_method = state_data.get('from_method'); to_method = state_data.get('to_method')

    if from_method == "사다리차 🪜":
        ladder_cost, ladder_note = get_ladder_cost(from_floor_num, selected_vehicle)
        if ladder_cost > 0: cost_items.append(("출발지 사다리차", ladder_cost, ladder_note)); total_cost += ladder_cost
        elif ladder_note != "1층 이하": cost_items.append(("출발지 사다리차", 0, ladder_note))
    if to_method == "사다리차 🪜":
        ladder_cost, ladder_note = get_ladder_cost(to_floor_num, selected_vehicle)
        dest_label = "도착지";
        if ladder_cost > 0: cost_items.append((f"{dest_label} 사다리차", ladder_cost, ladder_note)); total_cost += ladder_cost
        elif ladder_note != "1층 이하": cost_items.append((f"{dest_label} 사다리차", 0, ladder_note))

    sky_total_cost = 0; sky_notes_list = []; sky_hours_from = state_data.get('sky_hours_from', 1); sky_hours_final = state_data.get('sky_hours_final', 1);
    try: sky_hours_from = max(1, int(sky_hours_from)); except: sky_hours_from = 1
    try: sky_hours_final = max(1, int(sky_hours_final)); except: sky_hours_final = 1
    sky_base = getattr(data, 'SKY_BASE_PRICE', 300000); sky_extra = getattr(data, 'SKY_EXTRA_HOUR_PRICE', 70000)
    if from_method == "스카이 🏗️": cost = sky_base + sky_extra * (sky_hours_from - 1); note = f"출발({sky_hours_from}h): {sky_base:,}"; if sky_hours_from > 1: note += f" + 추가 {sky_extra*(sky_hours_from-1):,}"; sky_total_cost += cost; sky_notes_list.append(note)
    if to_method == "스카이 🏗️": cost = sky_base + sky_extra * (sky_hours_final - 1); note = f"도착({sky_hours_final}h): {sky_base:,}"; if sky_hours_final > 1: note += f" + 추가 {sky_extra*(sky_hours_final-1):,}"; sky_total_cost += cost; sky_notes_list.append(note)
    if sky_total_cost > 0: cost_items.append(("스카이 장비", sky_total_cost, " | ".join(sky_notes_list))); total_cost += sky_total_cost

    add_men = state_data.get('add_men', 0); add_women = state_data.get('add_women', 0); # Use original keys if unchanged in Tab3 UI
    try: add_men = int(add_men) if add_men is not None else 0; except: add_men = 0
    try: add_women = int(add_women) if add_women is not None else 0; except: add_women = 0
    additional_person_cost = getattr(data, 'ADDITIONAL_PERSON_COST', 200000)
    manual_added_cost = (add_men + add_women) * additional_person_cost
    if manual_added_cost > 0: cost_items.append(("추가 인력", manual_added_cost, f"남{add_men}, 여{add_women}")); total_cost += manual_added_cost

    auto_added_men = 0

    remove_base_housewife = state_data.get('remove_base_housewife', False) # Use original key if unchanged in Tab3 UI
    actual_remove_housewife = False
    if remove_base_housewife and base_women > 0:
        discount = -additional_person_cost * base_women
        cost_items.append(("기본 여성 인원 제외 할인", discount, f"여 {base_women}명 제외")); total_cost += discount
        actual_remove_housewife = True

    # *** 비용 조정 금액 읽을 때 새 키 사용 ('tab3_adjustment_amount') ***
    adjustment_amount_raw = state_data.get('tab3_adjustment_amount', 0)
    print(f"DEBUG: Raw adjustment_amount (from tab3_): {adjustment_amount_raw} (Type: {type(adjustment_amount_raw)})")
    try: adjustment_amount = int(adjustment_amount_raw); print(f"DEBUG: Converted adjustment_amount: {adjustment_amount}")
    except (ValueError, TypeError): adjustment_amount = 0; print(f"DEBUG: adjustment_amount conversion failed, defaulted to 0")

    if adjustment_amount != 0:
        adj_label = "할증 조정" if adjustment_amount > 0 else "할인 조정"
        print(f"DEBUG: Applying adjustment: Label='{adj_label}', Amount={adjustment_amount}")
        cost_items.append((f"{adj_label} 금액", adjustment_amount, "")); total_cost += adjustment_amount
    else: print(f"DEBUG: No adjustment applied (amount is 0).")

    if is_storage:
        duration = state_data.get('storage_duration', 1); selected_storage_type = state_data.get('storage_type', data.DEFAULT_STORAGE_TYPE if hasattr(data, 'DEFAULT_STORAGE_TYPE') else "")
        try: duration = max(1, int(duration)); except: duration = 1
        storage_rates = getattr(data, 'STORAGE_RATES_PER_DAY', {})
        default_storage_type = getattr(data, 'DEFAULT_STORAGE_TYPE', list(storage_rates.keys())[0] if storage_rates else "")
        daily_rate = storage_rates.get(selected_storage_type, storage_rates.get(default_storage_type, 0))
        if daily_rate > 0: cost = daily_rate * duration; cost_items.append(("보관료", cost, f"{selected_storage_type}, {duration}일 기준")); total_cost += cost
        else: cost_items.append(("오류", 0, f"보관 유형({selected_storage_type}) 요금 정보 없음"))

    apply_long = state_data.get('apply_long_distance', False); selector = state_data.get('long_distance_selector')
    if apply_long and selector and selector != "선택 안 함":
        cost = data.long_distance_prices.get(selector, 0)
        if cost > 0: cost_items.append(("장거리 운송료", cost, selector)); total_cost += cost

    has_waste = state_data.get('has_waste_check', False); tons = state_data.get('waste_tons_input', 0.5); # Use original keys if unchanged in Tab3 UI
    try: tons = float(tons) if tons is not None else 0.5; tons = max(0.5, tons); except: tons = 0.5
    waste_cost_per_ton = getattr(data, 'WASTE_DISPOSAL_COST_PER_TON', 300000)
    if has_waste: cost = waste_cost_per_ton * tons; cost_items.append(("폐기물 처리(톤)", cost, f"{tons:.1f}톤 기준")); total_cost += cost

    date_surcharge = 0; date_notes = []; date_opts = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
    special_day_prices = getattr(data, 'special_day_prices', {})
    for i, option in enumerate(date_opts):
        # *** 날짜 할증 읽을 때 새 키 사용 ('tab3_date_opt_i_widget') ***
        if state_data.get(f"tab3_date_opt_{i}_widget", False): # Use new key
             surcharge = special_day_prices.get(option, 0);
             if surcharge > 0: date_surcharge += surcharge; date_notes.append(option)
    if date_surcharge > 0: cost_items.append(("날짜 할증", date_surcharge, ", ".join(date_notes))); total_cost += date_surcharge

    # --- *** 지방 사다리 추가요금 읽을 때 새 키 사용 ('tab3_regional_ladder_surcharge') *** ---
    regional_ladder_surcharge = state_data.get('tab3_regional_ladder_surcharge', 0) # Use new key
    try: regional_ladder_surcharge = int(regional_ladder_surcharge)
    except: regional_ladder_surcharge = 0
    if regional_ladder_surcharge > 0: cost_items.append(("지방 사다리 추가요금", regional_ladder_surcharge, "")); total_cost += regional_ladder_surcharge

    final_men = base_men + add_men + auto_added_men
    final_women = (base_women + add_women) if not actual_remove_housewife else add_women
    personnel_info = {'base_men': base_men, 'base_women': base_women, 'manual_added_men': add_men, 'manual_added_women': add_women, 'auto_added_men': auto_added_men, 'remove_base_housewife': actual_remove_housewife, 'final_men': final_men, 'final_women': final_women}

    print(f"DEBUG: total_cost *before* max(0, round(total_cost)): {total_cost}")
    final_total_cost = max(0, round(total_cost))
    print(f"DEBUG: final_total_cost *after* max(0, round(total_cost)): {final_total_cost}")
    print("-" * 30)

    return final_total_cost, cost_items, personnel_info