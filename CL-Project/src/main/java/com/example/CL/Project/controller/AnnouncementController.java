package com.example.CL.Project.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class AnnouncementController {

    // HTML 뷰 페이지 반환 전용 컨트롤러
    @GetMapping({ "/announcements" })
    public String announcementsPage() {
        // template/Announcement.html
        return "Announcement";
    }

    @GetMapping("/annRegistration") 
    public String registrationPage() {
        // template/AnnRegistration.html
        return "AnnRegistration";
    }

    @GetMapping("/postArticle")
    public String postArticlePage() {
        // template/PostArticle.html
        return "PostArticle";
    }    

}
