ROS2 入门总结（含全部命令）
一、核心概念（一句话）
程序拆成各干各的「节点」，靠「话题」发消息互相配合。

节点=程序（工人），话题=管道（传送带），消息=数据（零件）。

二、全部要用的命令
1. 每次开终端先加载 ROS2 环景
source /opt/ros/humble/setup.bash

2. 跑经典示例（两个终端）
ros2 run demo_nodes_cpp talker      # 终端1：发消息
ros2 run demo_nodes_cpp listener    # 终端2：收消息

3. 旁观查看（第三个终端）
ros2 node list              # 有哪些节点
ros2 topic list             # 有哪些话题
ros2 topic info /chatter    # 谁在发、谁在收
ros2 topic echo /chatter    # 实时偷看话题里的数据
ros2 topic info /chatter --verbose   # 看 QoS 等详细信息

4. 看节点图（图形界面）
ros2 run rqt_graph rqt_graph
图里：椭圆=节点，方框=话题，箭头=消息流向
刷新：点左上角蓝色循环箭头按钮（不会自动刷新）
关掉节点→点刷新→节点消失；重开→再刷新→箭头连上

5. 服务 / 参数（后续会用到）
ros2 service list                 # 有哪些服务
ros2 service call <服务名> <请求>  # 调用服务（一问一答）
ros2 param list <节点名>          # 看某节点的参数
ros2 param get <节点名> <参数名>  # 读参数
ros2 param set <节点名> <参数名> <值>  # 运行中改参数

三、本次排错命令（rqt_graph 打不开）
which python3                                # 看当前用的是哪个 Python（关键！）
python3 -c "import PyQt5; print('ok')"       # 测试某模块能不能找到
grep -n "penv" ~/.bashrc                     # 找出污染 PATH 的那行
sed -i '/Desktop\/penv\/bin/s/^/# /' ~/.bashrc   # 注释掉那行
排查思路： 报「No module named ...」先跑 which python3，看是不是别的 Python 顶替了系统 Python。改完 .bashrc 记得关掉所有终端重开。

四、一张表记住三种能力
能力	像什么	什么时候用	关键词
话题 Topic	广播	数据持续不断	publish / subscribe
服务 Service	打电话问事	偶尔问一下等回答	server / client
参数 Parameter	调旋钮	运行中改设置	param get / set
核心就两条： ROS2 的灵魂是「节点+话题」；环境报错先查 which python3。命令不背，跑几遍自然就记住了 👍
/********************************************************************************************/
看图节点
有的，看图这件事有几个点新手特别容易误会或漏掉，值得单独说说：

1. 箭头方向 = 数据流向，不是「谁先启动」
箭头永远从发布者指向订阅者：talker → /chatter → listener。
很多人以为箭头表示「谁先开、谁后开」，不是的。哪怕 listener 先开、talker 后开，箭头还是 talker → listener。它表达的是「消息往哪流」。

2. 图不是实时的，是「你点刷新那一刻的快照」
rqt_graph 不会自己动。你点一下刷新，它才去问一次「现在谁在跑」。所以：
节点刚启动 / 刚关闭，图上不会立刻变
而且 DDS 发现也有几秒延迟，所以点了刷新可能要等 1~2 秒，或者多点一次

3. 左上角那个下拉框（显示模式）很关键
你之前用的「hide dead」勾选框，其实和左上角的下拉菜单是一套：
模式	显示什么
Nodes only	只看节点，不看话题
Nodes/Topics (active)	只显示还活着的节点（默认）
Nodes/Topics (all)	活着 + 已死的都显示
你想看「哪些节点起过又挂了」，就切到 all，或者取消勾选 Hide: Dead。

4. 双击椭圆，能看节点的详细「户口」
双击某个节点椭圆，会列出它的：发布了哪些话题、订阅了哪些话题、提供了哪些服务等。相当于 ros2 node info <节点名> 的图形版。

5. 图里最值钱的用途：一眼看出「谁没连上」
这是 rqt_graph 真正的杀手锏。两个节点就算话题名一模一样，只要 QoS 不兼容，DDS 就不会让它们连上。这时图上会出现：
两个椭圆，话题方框「悬空」——一边有箭头、一边没箭头
或者两个节点各自连着一个同名话题，但中间断开
光看 ros2 topic list 是发现不了这个问题的，但 rqt_graph 一眼就看出来了。

6. 图会「越长越大」，但不用怕
一个话题可以被多个节点订阅，一个节点也能发/收多个话题。真实机器人上，图可能是一大团：


雷达 → /scan → 建图 → /map → 导航 → /cmd_vel → 电机
                 ↘ /map 也被 rviz2 订阅
节点越多，rqt_graph 越有用——因为它把「谁依赖谁」理清了。这也是我反复说「高手脑子里有张图」的原因。

最该记住的一条： 箭头是「数据流向」，图是「手动刷新的快照」，图的真正价值是找出没连上的地方。


