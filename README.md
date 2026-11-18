# 管廊测线交班台

市政管廊巡测班白天登记原测和复测的有向折线并封存接触证据。夜班只凭包号领取证据，选取甲线里程窗签发。次班可以在资料更正、来源停用或数据库重开后，按原号码复查原始交班成果。

使用 Python 3.11，依赖均来自标准库。以下命令从项目根目录执行，回归与演示各自使用临时数据库。

```console
python -m handover.desk verify
python -m handover.desk demo
python -m unittest discover -s tests -t . -v
```

## 从登记到领取

```python
from handover.desk import HandoverDesk

with HandoverDesk('patrol.sqlite3') as desk:
    a = desk.register('A', [(0, 0, 0), (4, 0, 4), (0, 0, 8)])
    b = desk.register('B', [(3, 0, 0), (2, 0, 1), (1, 0, 2)])
    order_id = desk.order(a, b)
    receipt = desk.publish(order_id)
    desk.retire(a)
    desk.retire(b)
    package = desk.get_package(receipt.package_id)
    report = desk.issue(receipt.package_id, 2, 6)
    assert desk.get_report(report.report_id) == report
    assert desk.get_receipt(receipt.receipt_id) == receipt
```

- `register(line_code, vertices)` 接受非空测线名和至少两个有序 `(x, y, station)` 顶点。各值接受 `int`、`Fraction` 或 `Fraction` 可解析的字符串。坐标、里程均以米计，计算和往返编码均精确。相邻坐标不同，里程严格递增。可以回走或自交。同名更正追加修订号，旧修订保持原值。`retire(revision_id)` 停用指定修订，重复停用同一修订有效。
- `order(a_revision_id, b_revision_id)` 按明确的甲乙修订号建待办。`publish(order_id)` 在同一事务中复查可用性、封存包、签交班回执、完成委托。成功返回含 `receipt_id`、`order_id` 和 `package_id` 的 `SealReceipt`。同一委托只可成功发布一次，提交失败后可重试。
- `get_package(package_id)` 返回版本 1 包的固定证据。包包含有序修订号、双方里程边界、原段数和按原段对排序的 `contacts`。每行列出一基原段号和两个 `(a_station, b_station, x, y)` 端点。点交的两端相同，重合按甲里程递增记录。空包也能领取。
- `issue(package_id, left, right)` 在包内甲线范围中接受有理闭窗。沿双侧里程都接续且乙向一致的片段归并，然后按各片原有比例截窗。返回含 `report_id`、`package_id`、`window` 与 `contacts` 的 `WindowReport`。结果端点是 `(甲里程, 乙里程)`，按甲起点、乙起点、甲终点、乙终点排序。`kind` 为 `same`、`reverse` 或 `point`。等端点窗口、空报告均合法。`get_report(report_id)` 和 `get_receipt(receipt_id)` 按原号读取存档。
- 参数和业务状态不合法时抛出 `ValueError`，未知号码抛出 `LookupError`。SQLite 错误上抛且该次写事务回滚。封存回滚后包、回执、委托完成状态均无新增。签发回滚后报告和取件引用均无新增。构造交班台时自动初始化，`desk.initialize()` 可重复执行并保留现有内容。

样例中的甲线两次经过同一区间，封存时各保留两个原段对。全窗报告反向 `(1,2) → (3,0)` 与同向 `(5,0) → (7,2)`。甲窗 `[2,6]` 得到 `(2,1) → (3,0)` 与 `(5,0) → (6,1)`。若乙线标定改为 `0, 1, 4`，甲窗 `[3/2,3/2]` 的单点是 `(3/2,5/2)`。样例目录还含一份可独立核账的固定包。
