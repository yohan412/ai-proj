package com.example.CL.Project.dto;

import lombok.Data;
import lombok.NoArgsConstructor;

@Data               // getter·setter·toString 자동 생성
@NoArgsConstructor  
public class LoginForm {
    private String username;
    private String password;
}
