<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns="http://www.isotc211.org/2005/gmd"
                xmlns:gco="http://www.isotc211.org/2005/gco"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  
    <xsl:output method="xml" indent="yes"/>

    <xsl:template match="@* | node()">
        <xsl:copy>
            <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
    </xsl:template>

  <xsl:template match="*[gco:CharacterString]">
    <xsl:copy>
      <xsl:apply-templates select="@*[not(name()='gco:nilReason')]"/>
      <xsl:choose>
        <xsl:when test="normalize-space(gco:CharacterString)=''">
          <xsl:attribute name="gco:nilReason">
            <xsl:choose>
              <xsl:when test="@gco:nilReason">
                <xsl:value-of select="@gco:nilReason"/>
              </xsl:when>
              <xsl:otherwise>missing</xsl:otherwise>
            </xsl:choose>
          </xsl:attribute>
        </xsl:when>
        <xsl:when test="@gco:nilReason!='missing' and normalize-space(gco:CharacterString)!=''">
          <xsl:copy-of select="@gco:nilReason"/>
        </xsl:when>
      </xsl:choose>
      <xsl:apply-templates select="node()"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
