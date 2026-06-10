import datetime
import logging

import pandas as pd
import plotly.graph_objects as go

DAYS_RU = {
    0: "Пн",  # Понедельник
    1: "Вт",  # Вторник
    2: "Ср",  # Среда
    3: "Чт",  # Четверг
    4: "Пт",  # Пятница
    5: "Сб",  # Суббота
    6: "Вс",  # Воскресенье
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
        df = df[df["PointID"] == radio_point_id]
        if df.empty:
            raise ValueError(f"Нет данных для PointID {radio_point_id}")

        dates = sorted(df["SchDate"].unique())
        self.radio_point_id = radio_point_id
        self.radio_name = radio_name
        self.df = df
        self.dates = [pd.to_datetime(d) for d in dates]
        self._format_weights()
        self._format_dateetimes()

    def _format_weights(self):
        """Форматирование текста для всплывающих подсказок
        Group by SchDate, Start, new colunm Weight - sum of rows in group
        """
        self.df["BlockLen"] = self.df["Stop"] - self.df["Start"]
        self.blocks_df = (
            self.df.groupby(["SchDate", "Start"])
            .agg(
                BlockLen=(
                    "BlockLen",
                    "first",
                ),  # длина блока (одинаковая для всех в группе)
                TotalRealDur=("RealDur", "sum"),  # сумма RealDur по записям блока
            )
            .reset_index()
        )

        self.blocks_df["BlockLoad"] = self.blocks_df["TotalRealDur"] / self.blocks_df["BlockLen"]

    def _format_dateetimes(self):
        # Преобразование Start в часы и минуты
        self.blocks_df["Start_Hour"] = self.blocks_df["Start"] // 3600
        self.blocks_df["Start_Minute"] = (self.blocks_df["Start"] % 3600) // 60
        # Преобразование времени в часы с десятичной дробью для оси Y
        self.blocks_df["Start_Hours_Decimal"] = (
            self.blocks_df["Start_Hour"] + self.blocks_df["Start_Minute"] / 60
        )
        # Преобразование в datetime
        self.blocks_df["SchDate"] = pd.to_datetime(self.blocks_df["SchDate"])

    def _get_detailed_texts(self, date):
        day_df = self.blocks_df[self.blocks_df["SchDate"] == date]
        block_starts = day_df["Start"].tolist()
        hover_texts = []
        day_data = self.df[self.df["SchDate"] == date]
        for st in block_starts:
            start_time_str = f"{st//3600:02d}:{(st%3600)//60:02d}"
            response_names_in_block = day_data[day_data["Start"] == st]["Responsible"].tolist()
            tracks_in_block = day_data[day_data["Start"] == st]["Clip"].tolist()
            responses_to_show = ""
            for t, r in zip(tracks_in_block, response_names_in_block):
                responses_to_show += f" {r} - {t}<br>"
            
            hover_texts.append(start_time_str + "<br>" + responses_to_show)
        return hover_texts

    def _get_block_load_texts(self, date):
        day_df = self.blocks_df[self.blocks_df["SchDate"] == date]
        block_loads = day_df["BlockLoad"].tolist()
        block_starts = day_df["Start"].tolist()
        block_lengths = day_df["BlockLen"].tolist()
        total_real_durations = day_df["TotalRealDur"].tolist()
        hover_texts = [
                f"""
Дата: <b>{date.strftime('%d-%m-%Y')}</b><br>
Начало: {datetime.timedelta(seconds=bs)}<br>
Длина блока: {datetime.timedelta(seconds=bl)}<br>
Занято: {datetime.timedelta(seconds=trd)}<br>
Свободно: {datetime.timedelta(seconds=max(0, bl - trd))}<br>
Загрузка: {load:.0%}"""
                for bs, bl, trd, load in zip(
                    block_starts, block_lengths, total_real_durations, block_loads
                )
            ]
        return hover_texts

    def create_schedule_fig(self, detailed=True):
        """
        Визуализация расписания роликов для 30 дней
        """

        x_labels = [_format_dates(d) for d in self.dates]

        fig = go.Figure()

        # Для каждого дня создаем scatter plot с точками
        for idx, date in enumerate(self.dates):
            day_df = self.blocks_df[self.blocks_df["SchDate"] == date]
            block_loads = day_df["BlockLoad"].tolist()
            y_values = day_df["Start_Hours_Decimal"].tolist()

            if detailed:
                hover_texts = self._get_detailed_texts(date)
            else:
                hover_texts = self._get_block_load_texts(date)

            block_colors = [
                "green" if load < 0.3 else "orange" if load < 0.6 else "red"
                for load in block_loads
            ]
            # Добавляем точки (время начала роликов)
            fig.add_trace(
                go.Scatter(
                    x=[idx] * len(y_values),
                    y=y_values,
                    mode="markers+text",
                    marker=dict(
                        size=[10 + w * 20 for w in block_loads],
                        color=block_colors,  # цвет зависит от y_values
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
                tickmode="array",
                tickvals=list(range(0, 25, 1)),
                ticktext=[f"{h:02d}:00" for h in range(0, 25, 1)],
                range=[0, 24],
                autorange="reversed",
                gridcolor="lightgray",
            ),
            margin=dict(l=50, r=30, t=70, b=120),
            height=1980,
            width=1024,
            hoverlabel=dict(bgcolor="white", font_size=11),
            plot_bgcolor="white",
            dragmode="pan",
        )

        return fig




# Пример использования
if __name__ == "__main__":
    # Создание тестовых данных
    df = pd.read_csv("scheds_orders_tmp.csv")

    # ID радиостанции для демонстрации
    radio_point_id = 1

    # Создание визуализатора и подготовка данных
    visualizer = RadioScheduleVisualizer(df, radio_point_id, radio_name="Some name")

    # Вывод первых строк для проверки
    print("Пример данных:")
    print(visualizer.df.head(10).to_string())
    visualizer.df.to_csv("data/scheds_orders_prepared.csv", index=False)
    # Запуск визуализации
    visualizer.create_schedule_fig().show()
