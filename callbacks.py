# callbacks.py
import streamlit as st

# Import necessary custom modules (ensure they exist)
try:
    import data
    # Import state manager constants if needed, e.g., for MOVE_TYPE_OPTIONS
    from state_manager import MOVE_TYPE_OPTIONS
except ImportError as e:
    st.error(f"Callbacks: 필수 모듈 로딩 실패 - {e}")
    st.stop()


# --- Callback Functions ---

def update_basket_quantities():
    """Callback to update basket quantities based on the final selected vehicle."""
    # Determine the effective selected vehicle first
    vehicle_choice = st.session_state.get('vehicle_select_radio', "자동 추천 차량 사용")
    selected_vehicle = None

    current_move_type = st.session_state.get('base_move_type', MOVE_TYPE_OPTIONS[0]) # Get current move type safely
    available_trucks_for_type = data.vehicle_prices.get(current_move_type, {}).keys()

    if vehicle_choice == "자동 추천 차량 사용":
        recommended_auto = st.session_state.get('recommended_vehicle_auto')
        # Check if auto-recommendation is valid for the current move type
        if recommended_auto and "초과" not in recommended_auto and recommended_auto in available_trucks_for_type:
             selected_vehicle = recommended_auto
    else: # Manual selection
        manual_choice = st.session_state.get('manual_vehicle_select_value')
        # Check if manual choice is valid for the current move type
        if manual_choice and manual_choice in available_trucks_for_type:
            selected_vehicle = manual_choice

    # Update final_selected_vehicle state regardless of whether baskets are updated
    st.session_state.final_selected_vehicle = selected_vehicle

    # Define basket section name (must match data.py)
    basket_section_name = "포장 자재 📦"
    item_defs_for_type = data.item_definitions.get(current_move_type, {})
    basket_items_in_def = item_defs_for_type.get(basket_section_name, [])

    # Update basket quantities if a valid vehicle with defaults is selected
    if selected_vehicle and selected_vehicle in data.default_basket_quantities:
        defaults = data.default_basket_quantities[selected_vehicle]
        for item, qty in defaults.items():
            # Ensure the item exists in the current move type's basket definition
            if item in basket_items_in_def:
                key = f"qty_{current_move_type}_{basket_section_name}_{item}"
                if key in st.session_state:
                    st.session_state[key] = qty
                # else: Optional: Initialize if key doesn't exist (should be handled by init)
    else:
        # Reset basket quantities if no valid vehicle is selected OR
        # the selected vehicle has no defaults defined (or if you prefer this behavior)
        for item in basket_items_in_def:
             key = f"qty_{current_move_type}_{basket_section_name}_{item}"
             if key in st.session_state:
                 st.session_state[key] = 0 # Reset to 0


def sync_move_type(widget_key):
    """Callback to sync base_move_type across tabs and update baskets."""
    if widget_key in st.session_state:
        new_value = st.session_state[widget_key]
        if st.session_state.get('base_move_type') != new_value:
            st.session_state.base_move_type = new_value
            # Sync the other tab's widget
            other_widget_key = 'base_move_type_widget_tab3' if widget_key == 'base_move_type_widget_tab1' else 'base_move_type_widget_tab1'
            if other_widget_key in st.session_state:
                 st.session_state[other_widget_key] = new_value
            # Update baskets based on the new move type and current vehicle selection
            update_basket_quantities()


def update_selected_gdrive_id():
    """Callback to update the selected Google Drive file ID based on filename selection."""
    # Use the unique key for the selectbox widget itself
    selected_name = st.session_state.get("gdrive_selected_filename_widget")
    if selected_name and 'gdrive_file_options_map' in st.session_state:
        # Update the main ID state variable
        st.session_state.gdrive_selected_file_id = st.session_state.gdrive_file_options_map.get(selected_name)
        # Optionally sync the non-widget filename state if needed elsewhere
        st.session_state.gdrive_selected_filename = selected_name
    # else:
    #     st.session_state.gdrive_selected_file_id = None
    #     st.session_state.gdrive_selected_filename = None