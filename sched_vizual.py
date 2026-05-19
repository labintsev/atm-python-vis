import datetime

import pandas as pd
import plotly.graph_objects as go

DAYS_RU = {
    0: 'Пн',  # Понедельник
    1: 'Вт',  # Вторник
    2: 'Ср',  # Среда
    3: 'Чт',  # Четверг
    4: 'Пт',  # Пятница
    5: 'Сб',  # Суббота
    6: 'Вс'   # Воскресенье
    }

def _format_dates(date: datetime.datetime) -> str:
    day_of_week = DAYS_RU[date.weekday()]
    return f"{day_of_week} {date.strftime('%d.%m.%Y')}"


class RadioScheduleVisualizer:
    """
    Класс для интерактивной визуализации расписания радиороликов
    """

    def __init__(self, df: pd.DataFrame, radio_point_id: int, radio_name: str = ""):
        """
        Инициализация визуализатора

        Args:
            df: DataFrame с данными
            radio_point_id: ID радиоточки
            radio_name: Название радиоточки
        """
        if df is None or df.empty:
            raise ValueError("DataFrame не может быть пустым")
        weekly_df = df[df["PointID"] == radio_point_id]
        if weekly_df.empty:
            print(f"Нет данных для PointID {radio_point_id}")
            return go.Figure()
        dates = sorted(weekly_df["SchDate"].unique())
        if len(dates) != 7:
            print(
                f"Ожидалось 7 дней данных, но найдено {len(dates)}."
            )
        self.radio_point_id = radio_point_id
        self.radio_name = radio_name
        self.df = weekly_df
        self.dates = [pd.to_datetime(d) for d in dates]
        self.weight_df = None
        self._format_weights()
        self._format_dateetimes()

    def _format_weights(self):
        """Форматирование текста для всплывающих подсказок
        Group by SchDate, Start, new colunm Weight - sum of rows in group      
        """

        self.weight_df = self.df.groupby(['SchDate', 'Start']).size().reset_index(name='Weight')


    def _format_dateetimes(self):
        # Преобразование Start в часы и минуты
        self.weight_df["Start_Hour"] = self.weight_df["Start"] // 3600
        self.weight_df["Start_Minute"] = (self.weight_df["Start"] % 3600) // 60


        # Преобразование времени в часы с десятичной дробью для оси Y
        self.weight_df["Start_Hours_Decimal"] = (
            self.weight_df["Start_Hour"] + self.weight_df["Start_Minute"] / 60
        )

        # Преобразование в datetime
        self.weight_df["Date"] = pd.to_datetime(self.weight_df["SchDate"])
        self.df["Date"] = pd.to_datetime(self.df["SchDate"])


    def create_detailed_schedule(self, radio_name: str = ""):
        """
        Визуализация расписания роликов для 7 дней
        """

        x_labels = [_format_dates(d) for d in self.dates]

        fig = go.Figure()

        # Цвета для разных Responsible
        unique_responsibles = self.df["Responsible"].unique()
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
        for idx, date in enumerate(self.dates):
            day_data = self.df[self.df["Date"] == date]
            weights = self.weight_df[self.weight_df["Date"] == date]
            block_weights = weights["Weight"].tolist()
            start_times = weights["Start"].tolist()
            hover_texts = []
            most_common_responsibles = []
            for st in start_times:
                start_time_str = f"{st//3600:02d}:{(st%3600)//60:02d}"
                response_names_in_block = day_data[day_data["Start"] == st]["Responsible"].tolist()
                tracks_in_block = day_data[day_data["Start"] == st]["Clip"].tolist()
                responses_to_show = ""
                for t, r in zip(tracks_in_block, response_names_in_block):
                    responses_to_show += f" {r} - {t}<br>"
                
                hover_texts.append(start_time_str + "<br>" + responses_to_show)
                most_common = max(set(response_names_in_block), key=response_names_in_block.count)
                most_common_responsibles.append(most_common)

            y_values = weights["Start_Hours_Decimal"].tolist()

            # Добавляем точки (время начала роликов)
            fig.add_trace(
                go.Scatter(
                    x=[idx] * len(y_values),
                    y=y_values,
                    mode="markers+text",
                    marker=dict(
                        size=[10 + w * 2 for w in block_weights],  # Размер точки пропорционален весу
                        color=[color_map.get(r, "#1E90FF") for r in most_common_responsibles],  # Цвет по ответственному
                        symbol="circle",
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
                title=f"{self.radio_point_id} - {self.radio_name}",
                tickmode="array",
                tickvals=list(range(len(self.dates))),
                ticktext=x_labels,
                tickangle=-45,
                gridcolor="lightgray",
                side="top",
            ),
            yaxis=dict(
                title="⏰ Время суток (часы)",
                tickmode="linear",
                tick0=0,
                dtick=1,
                tickvals=list(range(0, 25, 2)),
                ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)],
                range=[-0.5, 24],
                gridcolor="lightgray",
            ),
            margin=dict(l=50, r=30, t=70, b=120),            
            height=3000,
            width=1000,
            hoverlabel=dict(bgcolor="white", font_size=11),
            plot_bgcolor="white",
            dragmode='pan'
        )

        return fig

    def get_figure(self):
        """
        Получить Plotly Figure для интерактивной визуализации

        Returns:
            plotly.graph_objects.Figure объект
        """
        return self.create_detailed_schedule()


# Пример использования
if __name__ == "__main__":
    # Создание тестовых данных (7 дней)
    df = pd.read_csv("scheds_orders_tmp.csv")

    # Генерируем данные для 7 дней
    radio_point_id = 17

    # Разные ролики для демонстрации

    # Создание визуализатора и подготовка данных
    visualizer = RadioScheduleVisualizer(df, radio_point_id, radio_name="Some name")

    # Вывод первых строк для проверки
    print("Пример данных:")
    print(df.head(10))
    print("\n")

    # Запуск визуализации
    visualizer.get_figure().show()