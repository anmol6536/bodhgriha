from typing import Any, Generator, Iterable
from sqlalchemy import Engine, text, create_engine
from sqlalchemy.exc import ResourceClosedError
import pandas as pd
from pandas import DataFrame
import os


class EngineManager:
    _instances: dict[str, Engine] = dict(
        BODHGRIHA=create_engine(os.environ.get("DATABASE_URL"))
    )

    def __init__(self): ...

    @classmethod
    def get(cls, name: str) -> Engine:
        return cls._instances[name]


def execute(
    queries: list[str] | str,
    parameters: dict[str, Any] | None,
    engine: Engine,
    to_pandas: bool = True,
    commit: bool = False,
) -> DataFrame | Generator[Iterable, None, None]:
    """
    Execute one or more SQL queries on the given SQLAlchemy engine.

    :param queries: Single SQL string or list of SQL strings
    :param parameters: Optional parameters to bind
    :param engine: SQLAlchemy Engine
    :param to_pandas: If True, return DataFrame from last query
    :param commit: If True, commit transaction explicitly
    """
    queries = [queries] if isinstance(queries, str) else queries

    response = None
    try:
        with engine.begin() as connection:  # auto-commits or rolls back
            for query in queries:
                response = connection.execute(text(query), parameters or {})
            if commit:
                connection.commit()  # Only valid if using engine.connect(), not engine.begin()

    except Exception as e:
        # engine.begin() handles rollback automatically
        raise

    if response is None:
        return pd.DataFrame()

    if to_pandas:
        try:
            return pd.DataFrame(response.fetchall(), columns=response.keys())
        except ResourceClosedError:
            return pd.DataFrame()
    else:
        try:
            yield from response
        except ResourceClosedError:
            return None


if __name__ == "__main__":
    engine = EngineManager.get("BODHGRIHA")
    queries = [
        "create table test(id serial not null, value text not null)",
        "insert into test (value) VALUES ('a'), ('b'), ('c')",
        "drop table test;"
    ]
    print(list(execute(queries, None, engine, False, False)))