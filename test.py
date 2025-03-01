from app import PoolCalculator

# Тестовые размеры из КП
calculator = PoolCalculator(8000, 4000, 1650)

# Получаем все расчеты
concrete = calculator.calculate_concrete_works()
formwork = calculator.calculate_formwork()
total_cost = calculator.calculate_total_cost()

print("\nПроверка соответствия КП:")
print("-" * 50)
print(f"Бетон М300: {concrete['Бетон М300 (чаша)']}")
print(f"Бетон М200: {concrete['Бетон М200 (подбетонка)']}")
print(f"Общий объем бетона: {concrete['Общий объем бетона']}")
print(f"Арматура: {formwork['Арматура']}")
print(f"Количество фанеры: {formwork['Количество фанеры']}")
print(f"Общая стоимость: {total_cost:,} ₽")
print("-" * 50)
