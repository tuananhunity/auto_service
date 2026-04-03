"ui";

// --- Cấu hình giao diện ---
var color = "#2196F3";
ui.layout(
    <drawer id="drawer">
        <vertical>
            <toolbar id="toolbar" title="FB Auto Comment (AutoJS)" />
            <tabs id="tabs" />
            <viewpager id="viewpager">
                {/* Tab 1: Điều khiển */}
                <vertical>
                    <card w="*" h="auto" margin="10 5" cardCornerRadius="5" cardElevation="2dp" foreground="?selectableItemBackground">
                        <vertical padding="16">
                            <text text="BẢNG ĐIỀU KHIỂN" textColor="black" textSize="16sp" textStyle="bold" />
                            <text text="URL Nhóm (để trống sẽ dùng danh sách dán dưới đây)" margin="0 10 0 0" />
                            <input id="input_url" hint="https://www.facebook.com/groups/..." textSize="14sp" />
                            
                            <grid-layout columns="2" w="*">
                                <vertical w="*">
                                    <text text="Số bài / Nhóm" margin="0 5" />
                                    <input id="input_max_posts" text="5" inputType="number" />
                                </vertical>
                                <vertical w="*">
                                    <text text="Delay (giây)" margin="0 5" />
                                    <input id="input_delay" text="10" inputType="number" />
                                </vertical>
                            </grid-layout>

                            <horizontal margin="0 10 0 0">
                                <button id="btn_start" text="BẮT ĐẦU CHẠY" bg="#4CAF50" textColor="white" layout_weight="1" />
                                <button id="btn_stop" text="DỪNG LẠI" bg="#F44336" textColor="white" layout_weight="1" />
                            </horizontal>
                        </vertical>
                    </card>
                    <card w="*" h="auto" margin="10 5" cardCornerRadius="5" cardElevation="2dp">
                        <vertical padding="16">
                            <text text="TRẠNG THÁI" textStyle="bold" />
                            <text id="txt_status" text="Chờ lệnh..." textColor="#666666" />
                        </vertical>
                    </card>
                </vertical>

                {/* Tab 2: Dữ liệu */}
                <vertical scrollbars="vertical">
                    <card w="*" h="auto" margin="10 5" cardCornerRadius="5">
                        <vertical padding="16">
                            <text text="DANH SÁCH NHÓM (Dòng 1 URL)" textStyle="bold" />
                            <input id="input_groups" h="150" gravity="top" hint="https://..." />
                        </vertical>
                    </card>
                    <card w="*" h="auto" margin="10 5" cardCornerRadius="5">
                        <vertical padding="16">
                            <text text="NỘI DUNG COMMENTS (Dòng 1 câu)" textStyle="bold" />
                            <input id="input_comments" h="150" gravity="top" hint="Comment dạo nào..." />
                        </vertical>
                    </card>
                    <button id="btn_save" text="LƯU DỮ LIỆU" margin="10" />
                </vertical>

                {/* Tab 3: Nhật ký */}
                <vertical>
                    <com.stardust.autojs.core.console.ConsoleView id="console" w="*" h="*" />
                </vertical>
            </viewpager>
        </vertical>
    </drawer>
);

// --- Khởi tạo dữ liệu ---
ui.viewpager.setTitles(["Điều khiển", "Dữ liệu", "Nhật ký"]);
ui.tabs.setupWithViewPager(ui.viewpager);

var storage = storages.create("fb_bot_config");
ui.input_groups.setText(storage.get("groups", ""));
ui.input_comments.setText(storage.get("comments", ""));
ui.input_url.setText(storage.get("url", ""));

var running_thread = null;

// --- Sự kiện nút bấm ---

ui.btn_save.click(function() {
    storage.put("groups", ui.input_groups.getText().toString());
    storage.put("comments", ui.input_comments.getText().toString());
    storage.put("url", ui.input_url.getText().toString());
    toast("Đã lưu dữ liệu!");
});

ui.btn_start.click(function() {
    if (running_thread && running_thread.isAlive()) {
        toast("Bot đang chạy rồi!");
        return;
    }
    
    let url = ui.input_url.getText().toString();
    let maxPosts = parseInt(ui.input_max_posts.getText().toString());
    let delay = parseInt(ui.input_delay.getText().toString());
    let groupsText = ui.input_groups.getText().toString();
    let commentsText = ui.input_comments.getText().toString();

    let groups = groupsText.split("\n").filter(l => l.trim() !== "");
    if (url.trim() !== "") groups = [url.trim()];
    let comments = commentsText.split("\n").filter(l => l.trim() !== "");

    if (groups.length == 0 || comments.length == 0) {
        alert("Lỗi", "Vui lòng nhập danh sách nhóm và câu bình luận!");
        return;
    }

    ui.txt_status.setText("Đang khởi động...");
    ui.txt_status.setTextColor(colors.parseColor("#4CAF50"));

    running_thread = threads.start(function() {
        try {
            startBotLogic(groups, comments, maxPosts, delay);
        } catch (e) {
            console.error(e);
            ui.run(() => {
                ui.txt_status.setText("Lỗi: " + e.message);
                ui.txt_status.setTextColor(colors.RED);
            });
        }
    });
});

ui.btn_stop.click(function() {
    if (running_thread && running_thread.isAlive()) {
        running_thread.interrupt();
        ui.txt_status.setText("Đã dừng khẩn cấp!");
        ui.txt_status.setTextColor(colors.RED);
        toast("Đã dừng!");
    }
});

// --- Logic Tự động hóa chính ---

function startBotLogic(groups, comments, maxPosts, delay) {
    auto.waitFor(); // Chờ quyền Accessibility
    console.log("--- BẮT ĐẦU BOT ---");

    for (let i = 0; i < groups.length; i++) {
        let groupUrl = groups[i];
        console.log("Đang vào nhóm: " + groupUrl);
        
        // Mở URL qua Intent của Facebook
        app.startActivity({
            action: "VIEW",
            data: groupUrl,
            packageName: "com.facebook.katana"
        });
        sleep(5000); // Chờ FB load

        let commentCount = 0;
        while (commentCount < maxPosts) {
            console.log("Đang tìm bài đăng thứ " + (commentCount + 1));
            
            // Tìm nút Bình luận (hoặc ô nhập liệu)
            // Lưu ý: ID và Text có thể thay đổi tùy phiên bản FB, 
            // dưới đây là các Selector phổ biến
            let commentBtn = text("Bình luận").findOne(2000);
            if (!commentBtn) {
                // Thử tìm theo mô tả (desc)
                commentBtn = desc("Bình luận").findOne(2000);
            }

            if (commentBtn) {
                commentBtn.click();
                sleep(2000);

                let commentText = comments[Math.floor(Math.random() * comments.length)];
                console.log("Gõ bình luận: " + commentText);
                
                // Tìm ô nhập liệu và gõ
                let input = className("android.widget.EditText").findOne(3000);
                if (input) {
                    input.setText(commentText);
                    sleep(1000);
                    
                    // Tìm nút gửi (Thường là nút có desc "Gửi" hoặc icon mũi tên)
                    let sendBtn = desc("Gửi").findOne(1000) || text("Gửi").findOne(1000) || desc("Đăng").findOne(1000);
                    if (sendBtn) {
                        sendBtn.click();
                        commentCount++;
                        console.log("Đã bình luận thành công!");
                    } else {
                        // Thử nhấn nút Enter trên bàn phím ảo
                        KeyCode(66);
                        commentCount++;
                    }
                }
            }

            // Cuộn xuống bài tiếp theo
            scrollDown();
            sleep(delay * 1000);
        }
    }
    
    console.log("--- HOÀN THÀNH ---");
    ui.run(() => {
        ui.txt_status.setText("Hoàn thành tất cả!");
        ui.txt_status.setTextColor(colors.BLACK);
    });
}
