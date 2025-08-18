package com.example.CL.Project.study;

import java.io.InputStream;

import org.springframework.core.io.InputStreamResource;

//MultipartInputStreamFileResource.java: MultipartFile → Resource 변환 유틸
public class MultipartInputStreamFileResource extends InputStreamResource {
	private final String filename;
	public MultipartInputStreamFileResource(InputStream is, String name) {
	 super(is);
	 this.filename = name;
	}
	@Override public String getFilename() { return this.filename; }
	@Override public long contentLength() { return -1; } // 생략 가능
}
