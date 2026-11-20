# Cartographer 使用与问题总结（2D 纯激光雷达）

> 适用场景：ROS 2 Humble + 单线激光雷达（LD14P 实测）+ 无底盘里程计 + VMware 虚拟机
> 本项目配置文件：`/mnt/hgfs/astrapro/ld14p_2d.lua`

---

## 一、它是什么

| 项 | 内容 |
|---|---|
| 出品 | Google，2016 年开源（原为室内背包建图/街景采集） |
| 原理 | 前端：局部子图（submap）+ 实时相关性扫描匹配；后端：分支定界回环检测 + Ceres 位姿图优化 |
| 类型 | 图优化类 SLAM（和 slam_toolbox 同类，但匹配器更强、参数更多） |
| ROS 2 包 | `ros-humble-cartographer`、`ros-humble-cartographer-ros`（apt，2.0.9002） |
| 能做什么 | 2D 栅格地图、3D 点云地图、纯雷达 / 雷达+IMU / 雷达+里程计 |
| 不适合 | 需要实时避障（它只建图，不管避障）；极低算力设备 |

### 和 slam_toolbox 的关系

| | Cartographer | slam_toolbox |
|---|---|---|
| 匹配器 | 相关性匹配（分支定界）+ Ceres | Karto 扫描匹配 |
| 回环 | 强（全局子图搜索） | 一般（局部链式） |
| 里程计 | 可选，**能自己发 odom 帧** | 可选，但通常要外部 odom |
| 参数 | 多，学习曲线陡 | 少，开箱即用 |
| 适合 | 建图质量优先 | 快速上手 / 长期建图（lifelong） |

---

## 二、安装与依赖

```bash
sudo apt install -y ros-humble-cartographer ros-humble-cartographer-ros
sudo apt install -y ros-humble-nav2-map-server      # 存 pgm/yaml 用
```

验证：

```bash
ros2 pkg executables cartographer_ros
# cartographer_node
# cartographer_occupancy_grid_node
# cartographer_pbstream_map_publisher
# cartographer_pbstream_to_ros_map
```

---

## 三、配置体系

Cartographer 用 Lua 配置，分三层：

```
/opt/ros/humble/share/cartographer/configuration_files/
├── map_builder.lua          ← 全局（线程数、传感器类型）
├── trajectory_builder.lua   ← 插值、碰撞检查等
├── trajectory_builder_2d.lua← 2D 核心参数
├── pose_graph.lua           ← 回环与优化
└── ...
        ↑
        你的 ld14p_2d.lua 通过 include 继承，再覆盖需要的项
```

### 3.1 框架参数（必须和你的 TF 树一致）

| 参数 | 含义 | 本项目取值 |
|---|---|---|
| `map_frame` | 全局地图坐标系 | `map` |
| `tracking_frame` | 被跟踪的机体坐标系（必须有 IMU 时用 imu_link，纯雷达用 base_link） | `base_link` |
| `published_frame` | 发布位姿时的子坐标系 | `base_link` |
| `odom_frame` | 里程计坐标系名 | `odom` |
| `provide_odom_frame` | **true = Cartographer 自己发 odom→published_frame** | `true` |
| `use_odometry` | 是否订阅 `/odom` | `false`（纯雷达） |
| `publish_frame_projected_to_2d` | 是否把位姿投影到 2D | `false` |
| `lookup_transform_timeout_sec` | TF 查询超时 | `0.2` |

**三种典型 TF 配法：**

| 场景 | 配置 |
|---|---|
| 无里程计（本项目） | `provide_odom_frame=true`，`use_odometry=false`，**不要再外部发 odom→base_link** |
| 有轮式里程计 | `provide_odom_frame=false`，`use_odometry=true`，外部发 odom→base_link |
| 用 IMU | `tracking_frame=imu_link`，`use_imu_data=true`，`TRAJECTORY_BUILDER_2D.use_imu_data=true` |

### 3.2 传感器参数

| 参数 | 含义 | 本项目 |
|---|---|---|
| `num_laser_scans` | 2D 雷达话题数（订阅 `scan`） | `1` |
| `num_multi_echo_laser_scans` | 多回波雷达数 | `0` |
| `num_point_clouds` | 点云话题数（订阅 `points2`） | `0` |
| `num_subdivisions_per_laser_scan` | 一帧扫描拆成几份（高帧率雷达才需要 >1） | `1` |

### 3.3 2D 建图参数（最常调的）

| 参数 | 默认 | 含义 / 调整建议 |
|---|---|---|
| `TRAJECTORY_BUILDER_2D.min_range` | 0 | 小于此距离的点丢弃。**雷达 range_min=0 时建议设 0.05** |
| `TRAJECTORY_BUILDER_2D.max_range` | 30 | 大于此距离丢弃。本项目 12（LD14P 量程） |
| `TRAJECTORY_BUILDER_2D.missing_data_ray_length` | 5 | 无回波方向按此长度标记空闲。空旷环境可调小 |
| `TRAJECTORY_BUILDER_2D.use_imu_data` | true | 纯雷达必须设 false |
| `TRAJECTORY_BUILDER_2D.num_accumulated_range_data` | 1 | 累积几帧再插入子图。慢速时 1，高速可 2~3 |
| `TRAJECTORY_BUILDER_2D.voxel_filter_size` | 0.025 | 点云体素降采样尺寸 |
| `TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching` | false | **纯雷达建议 true**（没有里程计先验时的主力匹配） |
| `real_time_correlative_scan_matcher.linear_search_window` | 0.1 | 平移搜索窗口（米）。**抖动大就调小** |
| `real_time_correlative_scan_matcher.angular_search_window` | 20° | 角度搜索窗口 |
| `motion_filter.max_distance_meters` | 0.2 | 位移超过才插新节点 |
| `motion_filter.max_angle_radians` | 1° | 转角超过才插新节点 |
| `submaps.num_range_data` | 90 | 一个子图含多少帧数据。**调小→子图更细，回环更勤** |
| `submaps.resolution` | 0.05 | 子图分辨率 |

### 3.4 位姿图参数

| 参数 | 默认 | 含义 |
|---|---|---|
| `POSE_GRAPH.optimize_every_n_nodes` | 90 | 每插入多少节点优化一次。**调小→更准但更吃 CPU** |
| `POSE_GRAPH.constraint_builder.min_score` | 0.55 | 回环匹配最低分 |
| `POSE_GRAPH.constraint_builder.global_localization_min_score` | 0.6 | 全局定位最低分 |
| `POSE_GRAPH.constraint_builder.sampling_ratio` | 0.3 | 回环采样比例（越大越准越慢） |
| `POSE_GRAPH.optimization_problem.huber_scale` | 1e1 | 鲁棒核，越小越能抑制离群 |
| `POSE_GRAPH.max_num_final_iterations` | 200 | 最终优化迭代次数 |

---

## 四、启动流程

```bash
# 终端 A：雷达（必须已在发 /scan）
ros2 launch ldlidar ld14p.launch.py

# 终端 B：Cartographer 主节点
ros2 run cartographer_ros cartographer_node \
  -configuration_directory /mnt/hgfs/astrapro \
  -configuration_basename ld14p_2d.lua

# 终端 C：生成 /map（必须！否则没有地图话题）
ros2 run cartographer_ros cartographer_occupancy_grid_node \
  -resolution 0.05 -publish_period_sec 1.0
```

正常日志：

```
Found '.../map_builder.lua'
Found '.../trajectory_builder_2d.lua'
Added trajectory with ID '0'
scan rate: 6.00 Hz 1.67e-01 s +/- 7.85e-04 s
```

---

## 五、话题与服务

### 5.1 cartographer_node 发布

| 话题 | 类型 | 说明 |
|---|---|---|
| `/submap_list` | `cartographer_ros_msgs/SubmapList` | 子图列表（occupancy grid 节点消费） |
| `/scan_matched_points2` | `sensor_msgs/PointCloud2` | 匹配后的扫描点云 |
| `/trajectory_node_list` | `visualization_msgs/MarkerArray` | 轨迹节点 |
| `/constraint_list` | `MarkerArray` | 回环约束 |
| `/landmark_poses_list` | `MarkerArray` | 路标（一般空） |
| `/tf` | `tf2_msgs/TFMessage` | **map→odom→base_link（provide_odom_frame=true 时）** |

### 5.2 cartographer_node 订阅

`/scan`（或 remap 后的话题）、`/points2`、`/imu`、`/odom`、`/tf`

### 5.3 服务

| 服务 | 用途 |
|---|---|
| `/submap_query` | 查询指定子图（rviz/occupancy grid 用，慢机器上会 timeout 警告） |
| `/finish_trajectory` | 结束当前轨迹（保存前调用） |
| `/write_state` | 保存 `.pbstream`（完整状态，可续建） |
| `/start_trajectory` | 开始新轨迹 |
| `/delete_trajectory` | 删除轨迹 |
| `/trajectory_query` | 查询轨迹节点 |
| `/get_trajectory_states` | 轨迹状态 |
| `/read_metrics` | 内部指标（调试用） |

### 5.4 occupancy_grid_node 发布

| 话题 | 类型 | 说明 |
|---|---|---|
| `/map` | `nav_msgs/OccupancyGrid` | 1 Hz，**Durability = TRANSIENT_LOCAL** |
| `/map_updates` | `nav_msgs/OccupancyGridUpdate` | 增量更新 |
| `/map_metadata` | `nav_msgs/MapMetaData` | 元数据 |

---

## 六、RViz 配置（虚拟机必看）

```bash
LIBGL_ALWAYS_SOFTWARE=1 QT_QPA_PLATFORM=xcb ros2 run rviz2 rviz2
```

| 项 | 设置 |
|---|---|
| Global Options → Fixed Frame | **`map`** |
| Add → Map → Topic | `/map` |
| Map → **Durability Policy** | **`Transient Local`**（不改永远空白） |
| Map → Reliability | `Reliable` |
| Add → LaserScan → Topic | `/scan`，Size `0.03` |
| Add → TF | 勾 Show Names / Show Axes |
| 不要加 Submap 显示 | 会刷 `/submap_query timeout` |

---

## 七、保存地图

### 7.1 存成 pgm + yaml（给 nav2 用）

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/room1
```

### 7.2 存成 pbstream（完整状态，可续建/后处理）

```bash
ros2 service call /finish_trajectory cartographer_ros_msgs/srv/FinishTrajectory "{trajectory_id: 0}"
ros2 service call /write_state cartographer_ros_msgs/srv/WriteState "{filename: '/home/w/maps/room1.pbstream'}"
```

### 7.3 pbstream → pgm（离线转换，不用开节点）

```bash
ros2 run cartographer_ros cartographer_pbstream_to_ros_map \
  -pbstream_filename=/home/w/maps/room1.pbstream \
  -map_filestem=/home/w/maps/room1 \
  -resolution=0.05
```

---

## 八、离线建图（录包 → 反复重算）

```bash
# 1) 录包
ros2 bag record -o ~/bags/room1 /scan /tf /tf_static

# 2) 起 Cartographer（用仿真时钟）
ros2 run cartographer_ros cartographer_node \
  -configuration_directory /mnt/hgfs/astrapro \
  -configuration_basename ld14p_2d.lua \
  --ros-args -p use_sim_time:=true &

ros2 run cartographer_ros cartographer_occupancy_grid_node \
  -resolution 0.05 -publish_period_sec 1.0 --ros-args -p use_sim_time:=true &

# 3) 回放（可调速度、可反复重来）
ros2 bag play ~/bags/room1 --clock -r 0.5
```

好处：不受实时性/硬件掉线影响，可以反复调参重算。

---

## 九、常见问题与报错（重点）

### 9.1 启动 / 配置类

| 现象 | 原因 | 处理 |
|---|---|---|
| `Failed to open file: ld14p_2d.lua` | `-configuration_directory` 路径不对 | 必须指向 lua 所在**目录**，不是文件 |
| `Lua error: attempt to index a nil value` | lua 里引用了未定义变量 | 检查 include 是否齐全、参数名拼写 |
| 启动即退出、无日志 | 参数名写错（如 `-configuration_basename` 写成 `-config`） | 对照 `ros2 run cartographer_ros cartographer_node --help` |
| `Check failed: ... use_odometry` | `use_odometry=true` 但没有 `/odom` | 改成 false |

### 9.2 TF / 时间类

| 现象 | 原因 | 处理 |
|---|---|---|
| `Invalid frame ID "map" passed to canTransform` | Cartographer 还没处理第一帧扫描 | 确认 `/scan` 有数据；等 5 秒 |
| `No transform from [base_laser] to [base_link]` | 雷达 launch 没起（缺静态 TF） | 重开 `ros2 launch ldlidar ld14p.launch.py` |
| `Lookup would require extrapolation into the future` | 时间戳超前于 TF 缓存 | 检查 `date`；加重 `tf_buffer_duration`；重启节点 |
| **`Ignored subdivision of a LaserScan message ... previous subdivision time P is not before current C`** | 扫描时间戳**倒退**（多个发布者、或时钟回退） | ✅ 本项目实测：`/scan` 有 3 个发布者。`pkill -9 -f ldlidar` 后只启一个 |
| `Dropped N earlier points` | 累积窗口外的旧点被丢 | 少量（1~2 点）正常；几百个说明时间戳乱 |

### 9.3 运行 / 性能类

| 现象 | 原因 | 处理 |
|---|---|---|
| `failed to send response to /submap_query (timeout)` | rviz 拉子图太慢（虚拟机 CPU） | 关掉 RViz 的 Submap 显示；或忽略 |
| `Requested submap N ... does not exist: maybe it has been trimmed` | 请求了已被裁剪的旧子图 | 正常现象，无害 |
| `Failed to compute constraint` | 回环匹配失败 | 降速、环境加特征；不改也能建图 |
| 地图不涨 / `map` 帧不存在 | 没收到扫描 / occupancy_grid 节点没起 | 查 `/scan` hz、查 `/map` publisher |
| CPU 100%、卡顿 | 虚拟机核数少 / 分辨率过高 | 降 `submaps.resolution`（0.05→0.08）、减 `num_background_threads` |
| 内存暴涨 | 长时间建图、子图不裁剪 | 减小 `POSE_GRAPH.max_num_final_iterations`、分段建图 |

### 9.4 地图质量类（本项目实际遇到）

| 现象 | 根因 | 解决 |
|---|---|---|
| **地图像烟雾/羽毛，墙不成线** | 每帧扫描几何不一致 | **驱动 `angle_increment` 每帧变化**（已打补丁固定为 2π/500） |
| **地图尺寸暴涨（几十米）** | 位姿漂移 | ① 多发布者 ② 雷达被近处物体包围 ③ 走太快 |
| **静止时地图还在涨** | 匹配在漂 | 雷达刚性固定；周围 1.5m 清空；中位测距应 2~5m |
| 墙有双层重影 | 回环没闭合 / 走太快 | 走回起点；≤0.3 m/s |
| 地图整体旋转/错位 | 回环误匹配 | 提高 `constraint_builder.min_score`（0.55→0.65） |

---

## 十、调参指南（按症状）

| 症状 | 调什么 | 方向 |
|---|---|---|
| 位姿抖、易跳变 | `real_time_correlative_scan_matcher.linear_search_window` | 0.1 → **0.05** |
| | `motion_filter.max_distance_meters` | 0.2 → **0.3**（少插节点） |
| 墙重影、闭合不上 | `POSE_GRAPH.constraint_builder.min_score` | 0.55 → **0.65**（更严） |
| | `submaps.num_range_data` | 90 → **60**（子图更细） |
| 回环太慢 | `POSE_GRAPH.optimize_every_n_nodes` | 90 → **30** |
| CPU 太高 | `POSE_GRAPH.optimize_every_n_nodes` | 90 → **150** |
| | `submaps.resolution` | 0.05 → **0.08** |
| 快速运动跟丢 | `num_accumulated_range_data` | 1 → **2~3** |
| 空旷环境乱建 | `missing_data_ray_length` | 5 → **1.0** |

---

## 十一、本项目实测记录（LD14P + 无里程计 + VMware）

| 项 | 数值 |
|---|---|
| 雷达帧率 | 6.00 Hz ±0.78 ms |
| 每帧点数 | 500（固定栅格），有效 437 |
| `angle_increment` | 0.012566（2π/500，补丁固定） |
| 中位测距 | 0.495 m（雷达被近处物体包围，需改善） |
| `/map` 频率 | 1.0 Hz |
| 曾出现的致命问题 | ① 驱动 `angle_increment` 抖动 ② `/scan` 3 个发布者 ③ 雷达摆位太憋屈 |

### 已验证有效的完整命令

```bash
# 清场
sudo pkill -9 -f ldlidar; sudo pkill -9 -f cartographer; sleep 2

# 雷达
ros2 launch ldlidar ld14p.launch.py

# SLAM
ros2 run cartographer_ros cartographer_node \
  -configuration_directory /mnt/hgfs/astrapro \
  -configuration_basename ld14p_2d.lua

# 地图
ros2 run cartographer_ros cartographer_occupancy_grid_node \
  -resolution 0.05 -publish_period_sec 1.0
```

---

## 十二、速查：三条判断命令

```bash
ros2 topic hz /scan                              # 6.0（数据在流）
ros2 topic info /scan | head -3                  # Publisher count: 1（无重复）
ros2 topic echo /scan --once --field angle_increment   # 0.012566（几何稳定）
ros2 run tf2_ros tf2_echo map base_laser         # 走动时应平滑变化
```
