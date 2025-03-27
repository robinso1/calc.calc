"""
Модуль kp_profiles.py
Содержит параметры расчета для разных коммерческих предложений.
"""

# Структура КП
KP1 = {
    "name": "КП №1 (8000x4000x1500)",
    "dimensions": {
        "length": 8000,
        "width": 4000,
        "depth": 1650,
        "wall_thickness": 200
    },
    "basic_dimensions": {
        "water_surface": 32.0,
        "perimeter": 26.0,
        "wall_area": 39.6,
        "finishing_area": 71.6,
        "water_volume": 48.0
    },
    "costs": {
        "materials_total": 817876,
        "works_total": 931860,
        "equipment_total": 1149928,
        "total": 2899664
    },
    # Цены для отделки
    "lining_price": 5400,     # Лайнер (цена за м²)
    "frame_price": 0,         # Каркасная стоимость
    "concrete_price": 6650,   # Бетон М-300 (цена за м³)
    
    # Цены для материалов (из КП "ДОН БАСС")
    "materials_prices": {
        "concrete": 6650,     # Цена бетона М300 за м³
        "concrete_m200": 5750, # Цена бетона М200 за м³
        "rebar": 65000,       # Цена арматуры за тонну
        "pvc_film": 5400,     # Лайнер (цена за м²)
        "tile": 2500,         # Цена за м² (не используется для KP1, т.к. там лайнер)
        "grout": 300,         # Цена за м²
        "waterproofing": 800, # Цена за м²
        "tile_adhesive": 400, # Цена за м²
        "coping_stone": 2600, # Копинговый камень (штука)
        "earthworks": 400     # Земляные работы (м³)
    },
    # Цены для работ (из КП "ДОН БАСС")
    "works_prices": {
        "earthworks": 400,       # руб/м³
        "concrete_works": 7000,  # руб/м³
        "reinforcement": 1750,   # руб/м²
        "waterproofing": 800,    # руб/м²
        "tile_laying": 2500,     # руб/м²
        "grouting": 300,         # руб/м²
        "equipment_installation": 186000,  # фиксированная цена
        "commissioning": 0,      # фиксированная цена
        "pool_works_price": 13000  # стоимость всех работ за м²
    },
    # Дополнительные параметры для КП
    "kp_params": {
        "coping_stone_count": 46,   # количество копингового камня
        "lining_area": 90,         # площадь лайнера м²
        "earth_volume": 122,       # объем земляных работ м³
        "trucks_count": 15,        # количество КАМАЗов
        "formwork_area": 89,       # площадь опалубки м²
        "plywood_sheets": 48,      # количество листов фанеры
        "rebar_weight": 1.8        # вес арматуры в тоннах
    }
}

KP2 = {
    "name": "КП №2 (8000x3000x1500)",
    "dimensions": {
        "length": 8000,
        "width": 3000,
        "depth": 1500,
        "wall_thickness": 200
    },
    "basic_dimensions": {
        "water_surface": 23.0,
        "perimeter": 22.0,
        "wall_area": 33.0,
        "finishing_area": 57.0,
        "water_volume": 34.5
    },
    "costs": {
        "materials_total": 583398,
        "works_total": 615690,
        "equipment_total": 929369,
        "total": 2128457
    },
    # Цены для отделки
    "lining_price": 0,         # Нет лайнера
    "frame_price": 0,          # Каркасная стоимость
    "concrete_price": 6650,    # Бетон М-300 (цена за м³)
    
    "materials_prices": {
        "concrete": 5000,  # Цена за м³
        "rebar": 80000,   # Цена за тонну
        "pvc_film": 1200, # Цена за м²
        "tile": 2500,     # Цена за м²
        "grout": 300,     # Цена за м²
        "waterproofing": 800,  # Цена за м²
        "tile_adhesive": 400   # Цена за м²
    },
    "works_prices": {
        "earthworks": 1500,      # руб/м³
        "concrete_works": 3500,  # руб/м³
        "reinforcement": 2500,   # руб/м³
        "waterproofing": 800,    # руб/м²
        "tile_laying": 2500,     # руб/м²
        "grouting": 300,         # руб/м²
        "equipment_installation": 15000,  # фиксированная цена
        "commissioning": 20000,  # фиксированная цена
        "pool_works_price": 10800  # стоимость всех работ за м²
    }
}

KP3 = {
    "name": "КП №3 (8000x3000x1500) - Упрощенный",
    "dimensions": {
        "length": 8000,
        "width": 3000,
        "depth": 1500,
        "wall_thickness": 200
    },
    "basic_dimensions": {
        "water_surface": 23.0,
        "perimeter": 22.0,
        "wall_area": 33.0,
        "finishing_area": 57.0,
        "water_volume": 34.5
    },
    "costs": {
        "materials_total": 320631,
        "works_total": 394284,
        "equipment_total": 728694,
        "total": 1443609
    },
    # Цены для отделки
    "lining_price": 0,         # Нет лайнера
    "frame_price": 0,          # Каркасная стоимость
    "concrete_price": 4800,    # Бетон М-300 (цена за м³)
    
    "materials_prices": {
        "concrete": 4800,  # Цена за м³
        "rebar": 75000,   # Цена за тонну
        "pvc_film": 1100, # Цена за м²
        "tile": 2300,     # Цена за м²
        "grout": 280,     # Цена за м²
        "waterproofing": 750,  # Цена за м²
        "tile_adhesive": 380   # Цена за м²
    },
    "works_prices": {
        "earthworks": 1400,      # руб/м³
        "concrete_works": 3300,  # руб/м³
        "reinforcement": 2300,   # руб/м³
        "waterproofing": 750,    # руб/м²
        "tile_laying": 2300,     # руб/м²
        "grouting": 280,         # руб/м²
        "equipment_installation": 14000,  # фиксированная цена
        "commissioning": 18000,  # фиксированная цена
        "pool_works_price": 6900  # стоимость всех работ за м²
    }
}

# Словарь профилей КП
PROFILES = {
    "kp1": KP1,
    "kp2": KP2,
    "kp3": KP3
}

def get_profile(profile_id="kp1"):
    """Получить параметры профиля КП по идентификатору
    
    Args:
        profile_id (str or dict): Идентификатор профиля (строка или словарь с ключом 'id')
        
    Returns:
        dict: Словарь с параметрами профиля. Если профиль не найден, возвращает профиль KP1
    """
    try:
        # Если profile_id — словарь, пытаемся извлечь id
        if isinstance(profile_id, dict):
            profile_id = profile_id.get("id", "kp1")
        
        # Проверяем, что profile_id — строка
        if not isinstance(profile_id, str):
            profile_id = "kp1"  # Значение по умолчанию
        
        # Проверяем, есть ли такой профиль в словаре PROFILES
        if profile_id not in PROFILES:
            print(f"Warning: Profile {profile_id} not found, using KP1 instead")
            return KP1
            
        return PROFILES.get(profile_id, KP1)
    except Exception as e:
        print(f"Error in get_profile: {str(e)}")
        return KP1  # Возвращаем KP1 в случае любой ошибки

def get_profiles_list():
    """Получить список всех доступных профилей КП"""
    return [{"id": key, "name": profile["name"]} for key, profile in PROFILES.items()]

def get_dimensions_correction_factor(profile_id, original_dimensions):
    """
    Получить коэффициент корректировки размеров
    
    Возвращает коэффициенты для корректировки расчетов, чтобы итоговые значения
    совпадали с указанными в КП
    """
    profile = get_profile(profile_id)
    
    # Рассчитываем теоретические размеры без корректировки
    length = original_dimensions["length"] / 1000
    width = original_dimensions["width"] / 1000
    depth = original_dimensions["depth"] / 1000
    
    theoretical_water_surface = length * width
    theoretical_perimeter = 2 * (length + width)
    theoretical_wall_area = theoretical_perimeter * depth
    theoretical_finishing_area = theoretical_water_surface + theoretical_wall_area
    theoretical_water_volume = theoretical_water_surface * depth
    
    # Коэффициенты корректировки - отношение ожидаемых значений к теоретическим
    return {
        "water_surface": profile["basic_dimensions"]["water_surface"] / theoretical_water_surface if theoretical_water_surface else 1,
        "perimeter": profile["basic_dimensions"]["perimeter"] / theoretical_perimeter if theoretical_perimeter else 1,
        "wall_area": profile["basic_dimensions"]["wall_area"] / theoretical_wall_area if theoretical_wall_area else 1,
        "finishing_area": profile["basic_dimensions"]["finishing_area"] / theoretical_finishing_area if theoretical_finishing_area else 1,
        "water_volume": profile["basic_dimensions"]["water_volume"] / theoretical_water_volume if theoretical_water_volume else 1,
    } 