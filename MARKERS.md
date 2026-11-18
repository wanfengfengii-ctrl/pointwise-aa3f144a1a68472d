# 按现场桩号领取复测区段

`README.md` 说明已有的登记、固定委托、发布、按实际里程签发及历史领取。现场桩号会随标定区改变，同一标签可落在不同的实际里程。桩号报告须让班组看到每条记录用的是哪两区的标签。

## 登记与发布

`HandoverDesk.register_calibrated(line_code, vertices, zones)` 返回固定修订号。测线名、顶点和同名追加规则沿用 `register`。`zones` 是非空有序序列，每项为 `(zone_id, station_left, station_right, marker_left, marker_right)`。`zone_id` 是本修订内唯一的非空字符串，甲乙各自的修订允许使用相同区号。四个数值接受与原里程相同的精确有理数输入。各区实际里程和区内桩号都须严格递增。按提交顺序检查全线首尾和相邻区界，实际里程须铺满全线且相邻区仅共享端点。标定区界可以落在原段内部。区内按两端作仿射标定，跨区桩号可跳号、回拨或相同。共享端点的两套标定各在本区有效，即使标签数值相同也保留区号。

沿原 `order` 和 `publish` 封存指定修订及其原接触。包固定两侧各自的标定事实与顺序，包号和原回执继续通过 `get_package` 与 `get_receipt` 领取。普通 `register` 登记无标定的修订。含一侧或两侧无标定的委托仍可发布并沿原接口按实际里程签发。新包的原接触仍供 `issue` 使用，旧包和旧报告维持原接口及解释。新增证据的内部持久结构自行设计。

## 签发与取件

`HandoverDesk.issue_by_marker(package_id, left, right)` 以有理数甲桩号闭窗签发。仅消费所指定的固定包和成功回执，包须具备双方标定。每个接触位置对所有有效的 `(甲区号, 乙区号)` 分别结算。甲标签在窗内即命中该区号对下的接触。范围求交和端点读值沿原接触片段的精确双里程关系。

同一区号对内，正长片段在两侧实际里程同时接续且乙向相同时归并成最大经过。孤立点按相同区号对及双里程对去重。只有同一区号对的正长结果在真实分段关系上覆盖该点时才省略该点。不同区号对的点和经过各自保留。同向与反向的端点均按甲实际里程递增排列。

返回报告提供 `report_id`、`package_id`、`window_kind`、`window`、`contacts`。`window_kind` 为 `marker`，`window.left`、`window.right` 保存原请求的精确桩号。`contacts` 为有序记录元组。每条记录提供 `kind`（`same`、`reverse` 或 `point`）、`a_zone_id`、`b_zone_id`、双里程对 `start`、`end`，以及对应的双桩号对 `marker_start`、`marker_end`。每对均按甲、乙次序排列，值为 `Fraction`。按甲起、乙起、甲终、乙终实际里程排序，并列再按甲区号、乙区号的字符串序排序。等点窗、无命中窗和具备双侧标定的空接触包都能签发，其中无命中结果为 `()`。

非法登记、非法窗、无效包、缺任一侧标定抛 `ValueError`，未知号码沿用 `LookupError`。发布及签发沿用现有事务和错误传播语义，失败没有部分成果。签发结果和取件引用同次提交。`get_report` 按原号读回本次请求与结果，即使停用、同名更正和重开也保持一致，读取不重算。普通里程签发保留原闭窗校验及返回接口。

## 样例和核验

`samples/marker-cases.json` 的每组包含甲乙顶点、标定区和查询。预期的每行依次是 `kind, a_zone_id, b_zone_id, start, end, marker_start, marker_end`。对照值中的字符串采用约分后的有理数写法。`back-numbered-return` 核对回拨后两段两点及无命中窗。`shared-zone-boundary` 核对同点四种归属、跨原段归并和有理等点窗。`crossing-at-original-vertices` 的四条原段对证据指向同一物理点，按区号对结算后交付两条记录。

完成后可在已发布 `back-numbered-return` 的同一 `desk` 中用以下方式沿用原提交失败夹具。`package_id` 取该次成功发布的回执。

```python
import sqlite3
from tests.support import fail_at_commit

with fail_at_commit(desk._connection, 'issue'):
    try:
        desk.issue_by_marker(package_id, 101, 102)
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError('expected the deferred commit failure')
```

核对提交失败前后的报告和取件引用，解除故障后用同包同窗重试。交付说明应写清包与报告怎样保存共享区界的身份。根目录的 `.pointwise-runtime.json` 沿用版本 1、`cli` 类型和现有命令约定。`setup` 是准备命令列表，`verify` 与 `demo` 各是一条命令，命令以参数数组表示。沿 `python -m handover.desk verify` 核对全部原测试及新增业务，断言失败返回非零。沿 `python -m handover.desk demo` 运行一次实际登记和发布，展示停源重开后按桩号领取的报告及按原号取得的存档。
