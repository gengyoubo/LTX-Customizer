package customizer;

import javax.swing.ImageIcon;
import javax.swing.JFrame;
import java.awt.Image;

public class Main {
    public static void main(String[] args) {
        // 创建一个 JFrame 窗口
        JFrame frame = new JFrame("LTX-Customizer");
        // 设置窗口的大小
        frame.setSize(400, 300);
        // 设置关闭操作，点击关闭按钮时退出程序
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        // 将窗口放在屏幕的中央
        frame.setLocationRelativeTo(null);
        // 加载图标文件 (确保图标文件在项目的路径中)
        ImageIcon icon = new ImageIcon("src/resources/picture/icon@400.png"); // 替换为你的图标路径
        Image image = icon.getImage();
        // 设置窗口图标
        frame.setIconImage(image);
        // 显示窗口
        frame.setVisible(true);
    }
}
