package customizer;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.net.URI;

public class Main {
    public static void main(String[] args) {
        final String SCREEN_TITLE = "LTX-Customizer";
        final String ICON_PATH = "src/resources/picture/icon@400.png"; // 图标的相对路径
        final String IMAGE_PATH = "src/resources/picture/github_64h.png"; // 图片的相对路径
        final String GITHUB_URL = "https://github.com/gengyoubo/LTX-Customizer"; // GitHub 项目链接
        final String GITHUB_URL_PERSONAL = "https://github.com/gengyoubo"; // GitHub 个人主页链接

        // 创建主窗口
        JFrame frame = createFrame(SCREEN_TITLE, 400, 300, ICON_PATH);

        // 创建按钮以跳转到修改窗口
        JButton modifyButton = new JButton("Go to Modify Window");
        modifyButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                // 创建修改窗口
                JFrame modifyFrame = createFrame("Modify Window", 400, 300, ICON_PATH);
                modifyFrame.setLayout(new FlowLayout());
                modifyFrame.add(new JLabel("Welcome to the Modify Window!")); // 示例内容
                modifyFrame.setVisible(true); // 显示修改窗口
                frame.setVisible(false); // 隐藏主窗口
            }
        });

        // 创建按钮以跳转到联系方式窗口
        JButton contactButton = new JButton("Go to Contact Window");
        contactButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                // 创建联系方式窗口
                JFrame contactFrame = createFrame("Contact Window", 400, 300, ICON_PATH);
                contactFrame.setLayout(new FlowLayout());

                // 添加联系方式
                contactFrame.add(new JLabel("联系方式：gengyoubo@gmail.com")); // 示例内容

                // 添加可点击的 GitHub 个人主页文本链接
                JLabel githubPersonalLinkLabel = new JLabel("<html><a href=''>" + GITHUB_URL_PERSONAL + "</a></html>");
                githubPersonalLinkLabel.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR)); // 设置鼠标指针为手形
                githubPersonalLinkLabel.addMouseListener(new MouseAdapter() {
                    @Override
                    public void mouseClicked(MouseEvent e) {
                        try {
                            Desktop.getDesktop().browse(new URI(GITHUB_URL_PERSONAL)); // 打开 GitHub 个人主页链接
                        } catch (Exception ex) {
                            JOptionPane.showMessageDialog(contactFrame, "无法打开链接: " + ex.getMessage());
                        }
                    }
                });

                contactFrame.add(githubPersonalLinkLabel); // 添加 GitHub 个人主页文本链接到联系方式窗口

                // 添加可点击的图片标签到联系方式窗口
                JLabel githubImageLabel = new JLabel();
                ImageIcon imageIcon = new ImageIcon(IMAGE_PATH); // 加载图片
                githubImageLabel.setIcon(imageIcon); // 设置图片图标
                githubImageLabel.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR)); // 设置鼠标指针为手形

                // 添加鼠标点击事件
                githubImageLabel.addMouseListener(new MouseAdapter() {
                    @Override
                    public void mouseClicked(MouseEvent e) {
                        try {
                            Desktop.getDesktop().browse(new URI(GITHUB_URL)); // 打开 GitHub 项目链接
                        } catch (Exception ex) {
                            JOptionPane.showMessageDialog(contactFrame, "无法打开链接: " + ex.getMessage());
                        }
                    }
                });

                contactFrame.add(githubImageLabel); // 添加 GitHub 图片标签到联系方式窗口

                contactFrame.setVisible(true); // 显示联系方式窗口
                frame.setVisible(false); // 隐藏主窗口
            }
        });

        // 使用简单布局管理器
        frame.setLayout(new FlowLayout()); // 设置窗口布局
        frame.add(modifyButton); // 添加修改按钮到窗口
        frame.add(contactButton); // 添加联系方式按钮到窗口

        // 显示窗口
        frame.setVisible(true);
    }

    // 创建并设置窗口的方法
    private static JFrame createFrame(String title, int width, int height, String iconPath) {
        JFrame frame = new JFrame(title); // 创建 JFrame
        frame.setSize(width, height); // 设置窗口大小
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE); // 设置关闭操作
        frame.setLocationRelativeTo(null); // 将窗口放在屏幕中央

        // 设置自定义图标
        ImageIcon icon = new ImageIcon(iconPath); // 加载图标
        Image image = icon.getImage(); // 获取图标图像
        frame.setIconImage(image); // 设置窗口图标

        return frame; // 返回设置好的窗口
    }
}
