import pandas as pd
import plotly.graph_objects as go


class RadioScheduleVisualizer:
    """
    Класс для интерактивной визуализации расписания радиороликов
    """

    def __init__(self, df: pd.DataFrame):
        """
        Инициализация визуализатора

        Args:
            df: DataFrame с данными
        """
        if df is None or df.empty:
            raise ValueError("DataFrame не может быть пустым")
        self.df = df
        self._prepare_data()

    def _prepare_data(self):
        """Подготовка данных для визуализации"""
        # Преобразование Start в часы и минуты
        self.df["Start_Hour"] = self.df["Start"] // 3600
        self.df["Start_Minute"] = (self.df["Start"] % 3600) // 60
        self.df["Start_Time"] = self.df["Start"].apply(
            lambda x: f"{x//3600:02d}:{(x%3600)//60:02d}"
        )

        # Преобразование времени в часы с десятичной дробью для оси Y
        self.df["Start_Hours_Decimal"] = (
            self.df["Start_Hour"] + self.df["Start_Minute"] / 60
        )

        # Преобразование в datetime
        self.df["Date"] = pd.to_datetime(self.df["SchDate"])

        # Длительность ролика в часах для высоты блока
        self.df["Duration_Hours"] = (self.df["Stop"] - self.df["Start"]) / 3600

        # Создание текста для всплывающей подсказки
        self.df["Tooltip_Text"] = self.df.apply(
            lambda row: f"<b>{row['Title']}</b><br>"
            + f"⏰ Время выхода: {row['Start_Time']}<br>"
            + f"📊 Длительность: {row['RealDur']} сек<br>"
            + f"🎬 Ролик: {row['Attach']}<br>"
            + f"🏢 Заказчик: {row['Customer']}<br>"
            + f"👤 Ответственный: {row['Responsible']}",
            axis=1,
        )

    def create_detailed_schedule(self, radio_id: str, radio_name: str = ""):
        """
        Визуализация расписания роликов для 7 дней
        """
        weekly_df = self.df[self.df["RadioID"] == radio_id]
        if weekly_df.empty:
            print(f"❌ Нет данных для RadioID {radio_id}")
            return go.Figure()
        dates = sorted(weekly_df["Date"].unique())
        if len(dates) != 7:
            print(
                f"⚠️ Ожидалось 7 дней данных, но найдено {len(dates)}."
            )

        x_labels = [d.strftime("%a %d.%m.%Y") for d in dates]

        fig = go.Figure()

        # Цвета для разных Responsible
        unique_responsibles = weekly_df["Responsible"].unique()
        color_palette = [
            "#FF6B6B",
            "#4ECDC4",
            "#45B7D1",
            "#96CEB4",
            "#FFEAA7",
            "#DDA0DD",
            "#98D8C8",
            "#FFB347",
            "#B0E0E6",
            "#FF69B4",
            "#87CEFA",
            "#FF6347",
            "#40E0D0",
            "#EE82EE",
            "#F08080",
            "#20B2AA",
        ]
        color_map = {
            responsible: color_palette[i % len(color_palette)]
            for i, responsible in enumerate(unique_responsibles)
        }

        # Для каждого дня создаем scatter plot с точками
        for idx, date in enumerate(dates):
            day_data = weekly_df[weekly_df["Date"] == date]

            # Подготовка данных для этого дня
            y_values = day_data["Start_Hours_Decimal"].tolist()
            texts = day_data["Start_Time"].tolist()
            hover_texts = day_data["Tooltip_Text"].tolist()
            responsibles = day_data["Responsible"].tolist()

            # Добавляем точки (время начала роликов)
            fig.add_trace(
                go.Scatter(
                    x=[idx] * len(y_values),
                    y=y_values,
                    mode="markers+text",
                    marker=dict(
                        size=50,
                        color=[color_map.get(r, "#1E90FF") for r in responsibles],
                        symbol="diamond-wide",
                        line=dict(color="black", width=1),
                        opacity=0.8,
                    ),
                    hovertext=hover_texts,
                    hoverinfo="text",
                    name=date.strftime("%Y-%m-%d"),
                    showlegend=False,
                )
            )

        fig.update_layout(
            xaxis=dict(
                title=f"{radio_id} - {radio_name}",
                tickmode="array",
                tickvals=list(range(len(dates))),
                ticktext=x_labels,
                tickangle=-45,
                gridcolor="lightgray",
                side="top",
            ),
            yaxis=dict(
                title="⏰ Время суток (часы)",
                tickmode="linear",
                tick0=0,
                dtick=2,
                tickvals=list(range(0, 25, 2)),
                ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)],
                range=[-0.5, 24],
                gridcolor="lightgray",
            ),
            height=1200,
            width=1200,
            hoverlabel=dict(bgcolor="white", font_size=11),
            plot_bgcolor="white",
        )

        return fig

    def get_figure(self, radio_id: int, radio_name: str = ""):
        """
        Получить Plotly Figure для интерактивной визуализации

        Args:
            radio_id: ID радиостанции
            radio_name: Название радиостанции

        Returns:
            plotly.graph_objects.Figure объект
        """
        return self.create_detailed_schedule(radio_id, radio_name)

    def interactive_visualization(self, radio_id: int, radio_name: str = ""):
        """
        Главная функция для интерактивной визуализации
        """

        # Создание визуализаций
        fig = self.get_figure(radio_id, radio_name)

        fig.show()


# Пример использования
if __name__ == "__main__":
    # Создание тестовых данных (7 дней)
    df = pd.read_csv("scheds_orders.csv")

    # Генерируем данные для 7 дней
    radio_id = 1

    # Разные ролики для демонстрации

    # Создание визуализатора и подготовка данных
    visualizer = RadioScheduleVisualizer(df)

    # Вывод первых строк для проверки
    print("Пример данных:")
    print(
        df[["SchDate", "Start", "Stop", "Customer", "Start_Time", "RadioID"]].head(10)
    )
    print("\n")

    # Запуск визуализации
    visualizer.interactive_visualization(radio_id=1, radio_name="Авторадио")
