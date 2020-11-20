<?xml version="1.0" encoding="UTF-8"?>
<!-- - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

Transformation to produce ISO19139 documents from input documents that
combine "extra" elements (Esri-specific or from ISO19115 DTD) with an included
MD_Metadata element.

The current version ignores all elements except for MD_Metadata, which is copied to the output verbatim.

author Heikki Doeleman
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -->
<xsl:stylesheet version="2.0" 
xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
xmlns:xs="http://www.w3.org/2001/XMLSchema" 
xmlns:gmd="http://www.isotc211.org/2005/gmd"
xmlns:gco="http://www.isotc211.org/2005/gco"
xmlns:gml="http://www.opengis.net/gml"
xmlns:gts="http://www.isotc211.org/2005/gts"               
xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
exclude-result-prefixes="#all"
>
	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
  
	<!-- the input document is supposed to have either <metadata> or <Metadata> as root element -->
	<xsl:template match="/metadata|/Metadata" priority ="10">
		<xsl:apply-templates/>
	</xsl:template>

	<!-- the wrapped <MD_Metadata> is copied in its entirety to the output -->
	<xsl:template match="gmd:MD_Metadata" priority ="10">
    <gmd:MD_Metadata>
      <xsl:apply-templates/>
    </gmd:MD_Metadata>
  </xsl:template>
		
	<!-- all these "extra" elements below are ignored -->
		
	<!-- ignore -->
	<xsl:template match="MetaID|Esri|FC_FeatureCatalogue|idinfo|dataIdInfo|metainfo|mdLang|mdStanName|mdStanVer|mdChar|mdHrLv|mdHrLvName|distinfo|distInfo|spdoinfo|spatRepInfo|eainfo|mdDateSt|spref|refSysInfo|dqInfo|Binary|dataqual|mdFileID|mdContact|dataset_description|ESRI_NL" priority ="10">
	</xsl:template>
  
  <!-- ignore -->
  <xsl:template match="gmd:MD_Metadata[name(parent::node())='gmd:MD_Metadata']" priority="10" />
  
  <!-- ignore -->
<!--
  <xsl:template match="gmd:*">
    <xsl:element name="gmd:{local-name()}" namespace="{namespace-uri()}">
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates select="node()" />
    </xsl:element>
  </xsl:template>
-->

  <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
</xsl:stylesheet>
