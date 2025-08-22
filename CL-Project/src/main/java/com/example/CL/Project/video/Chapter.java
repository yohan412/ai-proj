package com.example.CL.Project.video;

public class Chapter {
	  private double start;
	  private double end;
	  private String title;
	  private String summary;

	  public Chapter() {}
	  public Chapter(double start, double end, String title, String summary) {
	    this.start = start; this.end = end; this.title = title; this.summary = summary;
	  }
	  public double getStart() { return start; }
	  public void setStart(double start) { this.start = start; }
	  public double getEnd() { return end; }
	  public void setEnd(double end) { this.end = end; }
	  public String getTitle() { return title; }
	  public void setTitle(String title) { this.title = title; }
	  public String getSummary() { return summary; }
	  public void setSummary(String summary) { this.summary = summary; }
	}