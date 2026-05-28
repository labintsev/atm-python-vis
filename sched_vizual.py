import datetime
from json import load

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

        # 2. Группировка по дате и Start, суммируем RealDur
        self.df = (
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
        self.df["BlockLoad"] = (
            self.df["TotalRealDur"] / self.df["BlockLen"]
        )

    def _format_dateetimes(self):
        # Преобразование Start в часы и минуты
        self.df["Start_Hour"] = self.df["Start"] // 3600
        self.df["Start_Minute"] = (self.df["Start"] % 3600) // 60
        # Преобразование времени в часы с десятичной дробью для оси Y
        self.df["Start_Hours_Decimal"] = (
            self.df["Start_Hour"] + self.df["Start_Minute"] / 60
        )
        # Преобразование в datetime
        self.df["Date"] = pd.to_datetime(self.df["SchDate"])

    def create_detailed_schedule(self):
        """
        Визуализация расписания роликов для 30 дней
        """

        x_labels = [_format_dates(d) for d in self.dates]

        fig = go.Figure()

        # Для каждого дня создаем scatter plot с точками
        for idx, date in enumerate(self.dates):
            day_df = self.df[self.df["Date"] == date]
            block_loads = day_df["BlockLoad"].tolist()
            y_values = day_df["Start_Hours_Decimal"].tolist()
            # Время блока, длительность блока, суммарная длительность роликов в блоке
            block_times = day_df["Start"].tolist()
            block_lengths = day_df["BlockLen"].tolist()
            total_real_durations = day_df["TotalRealDur"].tolist()
            hover_texts = [
                f"""Начало: {datetime.timedelta(seconds=bt)}<br>
Длительность: {datetime.timedelta(seconds=bl)}<br>
Суммарная: {datetime.timedelta(seconds=trd)}<br>
Загрузка: {load:.0%}"""
                for bt, bl, trd, load in zip(
                    block_times, block_lengths, total_real_durations, block_loads
                )
            ]
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
            width=1024,
            hoverlabel=dict(bgcolor="white", font_size=11),
            plot_bgcolor="white",
            dragmode="pan",
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
    # Configure logging for main execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('logs/service.log'),
            logging.StreamHandler()
        ]
    )
    
    # Создание тестовых данных (7 дней)
    df = pd.read_csv("scheds_orders_tmp.csv")

    # ID радиостанции для демонстрации
    radio_point_id = 17

    # Создание визуализатора и подготовка данных
    visualizer = RadioScheduleVisualizer(df, radio_point_id, radio_name="Some name")

    # Вывод первых строк для проверки
    logger.info("Пример данных:")
    logger.info(f"\n{df.head(10).to_string()}")

    # Запуск визуализации
    visualizer.get_figure().show()
